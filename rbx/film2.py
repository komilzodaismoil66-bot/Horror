"""Roblox-style cinematic short, full cut (~1:48, 9:16), built and rendered with Blender (bpy, Cycles CPU).

python3 film2.py render START END [STEP]   render frames to frames2/####.png
python3 film2.py still FRAME [FRAME..]     single frames to stills/
Env: SAMPLES, RES (e.g. 540x960), THREADS
"""
import json
import math
import os
import random
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

import film as F1                  # resets the scene on import; gives the base pose library
import chars
import world as Wd
from world import F, FPS

HERE = os.path.dirname(os.path.abspath(__file__))
D = math.radians
END_T = 105.5
T_BOSS = 55.0
EVENTS = dict(impacts=[], shakes=[], whoosh=[], land=[], step=[], bstep=[], shatter=[], teleport=[],
              tremor=[(55.0, 62.0), (95.4, 97.5)], cut=END_T, cuts=[], boss_in=T_BOSS, wave=97.5, charge=95.6)

POSES = dict(F1.POSES)
POSES.update({
    'spread': dict(z=2.0, torso=(-10, 0, 0), head=(-12, 0, 0), armL=(0, 100, 0), armR=(0, -100, 0),
                   legL=(0, 10, 0), legR=(0, -10, 0)),
    'tie': dict(z=2.0, torso=(0, 0, 0), head=(8, 0, 0), armL=(0, 7, 0), armR=(-78, 0, -52), legL=(0, 0, 0),
                legR=(0, 0, 0)),
    'fists': dict(z=1.93, torso=(6, 0, 0), head=(-6, 0, 0), armL=(-28, 14, 10), armR=(-28, -14, -10),
                  legL=(-8, 6, 0), legR=(6, -6, 0)),
    'float': dict(z=2.0, torso=(-4, 0, 0), head=(22, 0, 0), armL=(0, 28, 0), armR=(0, -28, 0),
                  legL=(-12, 3, 0), legR=(8, -3, 0)),
    'stagger': dict(z=1.85, torso=(-14, 0, 10), head=(-10, 0, 0), armL=(-30, 30, 0), armR=(20, -40, 0),
                    legL=(-25, 0, 0), legR=(15, 0, 0)),
    'pant': dict(z=1.8, torso=(26, 0, 0), head=(-4, 0, 0), armL=(-12, 12, 0), armR=(-12, -12, 0),
                 legL=(-16, 6, 0), legR=(10, -6, 0)),
})
JOINTS = F1.JOINTS
WARM = (1.0, 0.85, 0.6)
COLD = (0.75, 0.85, 1.0)
RED = (1.0, 0.22, 0.12)


def V2(p):
    return Vector((p[0], p[1]))


def unit(v):
    return v.normalized() if v.length > 1e-6 else Vector((1, 0))


def toward(p, q, d):
    """Point at distance d from q on the line q->p."""
    p, q = V2(p), V2(q)
    return q + unit(p - q) * d


class Actor:
    def __init__(self, rig):
        self.rig = rig
        self.loc = Vector((0, 0))
        self.rz = 0.0
        self.last_t = -1.0
        self.last = None
        self.queue = []
        self.track = []

    @property
    def xy(self):
        return Vector((self.loc.x, self.loc.y))

    def face_angle(self, tgt):
        dx, dy = tgt[0] - self.loc.x, tgt[1] - self.loc.y
        if abs(dx) + abs(dy) < 1e-4:
            return self.rz
        a = math.atan2(dx, -dy)
        while a - self.rz > math.pi:
            a -= 2 * math.pi
        while a - self.rz < -math.pi:
            a += 2 * math.pi
        return a

    def _key(self, t, name, z, rx, over):
        p = dict(POSES[name])
        p.update(over)
        joints = {j: tuple(D(v) for v in p[j]) for j in JOINTS}
        self.rig.key(F(t), loc=(self.loc.x, self.loc.y, z), rot=(D(rx), 0, self.rz), **joints)
        self.track.append((t, self.loc.x, self.loc.y, z))

    def flush(self, t):
        q, self.queue = self.queue, []
        for (qt, name, kw) in q:
            if qt <= t - 0.09:
                self.pose(qt, name, **kw)

    def later(self, t, name, **kw):
        self.queue.append((t, name, kw))

    def pose(self, t, name, loc=None, face=None, z=None, rx=None, **over):
        if self.queue:
            self.flush(t)
        p = POSES[name]
        if loc is not None:
            self.loc = Vector((loc[0], loc[1]))
        zz = p['z'] if z is None else z
        if loc is not None and len(loc) == 3:
            zz = loc[2]
        if face is not None:
            self.rz = self.face_angle(face)
        rxx = p.get('rx', 0) if rx is None else rx
        self._key(t, name, zz, rxx, over)
        self.last = (name, zz, rxx, over)
        self.last_t = max(self.last_t, t)

    def hold(self, t, bob=True):
        """Keep the current pose until t (with a little breathing so nobody freezes)."""
        if self.queue:
            self.flush(t)
        if t <= self.last_t + 0.06 or self.last is None:
            return
        name, z, rx, over = self.last
        if bob and name != 'lie' and z <= 2.1:
            k, tt = 1, self.last_t + 0.42
            base = POSES[name]['torso'] if 'torso' not in over else over['torso']
            while tt < t - 0.25:
                o = dict(over)
                o['torso'] = (base[0] + 2.2 * (k % 2), base[1], base[2])
                self._key(tt, name, z - 0.05 * (k % 2), rx, o)
                tt += 0.42
                k += 1
        self._key(t, name, z, rx, over)
        self.last_t = t

    def at(self, t):
        tr = sorted(self.track)
        if t <= tr[0][0]:
            return Vector(tr[0][1:])
        for a, b in zip(tr, tr[1:]):
            if a[0] <= t <= b[0]:
                f = (t - a[0]) / max(1e-6, b[0] - a[0])
                return Vector(a[1:]).lerp(Vector(b[1:]), f)
        return Vector(tr[-1][1:])

    def sm(self, t, w=0.3):
        s = Vector((0, 0, 0))
        for d in (-w, -w / 2, 0, w / 2, w):
            s += self.at(t + d)
        return s / 5


def build_cast():
    return {k: Actor(chars.R6(k, chars.SPECS[k])) for k in ('suit', 'emo', 'mask', 'blue', 'boss')}


# =============================================================== choreography
def choreography(c):
    A, B, C, Dd, E = c['suit'], c['emo'], c['mask'], c['blue'], c['boss']
    ev = EVENTS
    rnd = random.Random(42)
    seed = [100]

    def sd():
        seed[0] += 1
        return seed[0]

    def hit(t, pos, size=1.0, color=WARM, dust_n=0, deb=0, wave=False):
        Wd.impact(t, pos, size, color)
        ev['impacts'].append((t, size))
        ev['shakes'].append((t, 9 * size))
        if dust_n:
            Wd.dust(t, (pos[0], pos[1], 0), n=dust_n, spread=3 * size, size=1.3 * size, seed=sd())
        if deb:
            Wd.debris(t, pos, n=deb, speed=9 * min(size, 1.6), seed=sd())
        if wave:
            Wd.shockwave(t, (pos[0], pos[1], 0.15), r_end=10 * size, dur=0.6)

    def run(act, t0, t1, p1, face=None, kind='run', step=None):
        p0, p1 = act.xy, V2(p1)
        act.hold(t0)
        step = step or (0.14 if kind == 'run' else 0.36)
        n = max(1, int(round((t1 - t0) / step)))
        far = p0 + (p1 - p0) * 20
        for k in range(1, n + 1):
            f = k / n
            t = t0 + (t1 - t0) * f
            act.pose(t, kind + ('A' if k % 2 else 'B'), loc=p0.lerp(p1, f), face=face if face is not None else far)
            ev['step'].append(t)

    def strike(att, dfn, t, move='punchR', res='block', power=1.0, kb=1.2, col=WARM, reach=2.7, side=1, frm=None):
        d, a0 = dfn.xy, att.xy
        a = toward(a0, d, reach) if frm is None else d - frm * reach
        dv = unit(d - a)
        att.hold(t - 0.24)
        att.pose(t - 0.12, 'antic', face=d, z=1.6)
        att.pose(t, move, loc=a, face=d)
        ev['whoosh'].append(t - 0.1)
        m = a + dv * (reach - 0.7)
        mid = (m.x, m.y, 3.0 if move == 'kick' else 3.7)
        if res == 'block':
            dfn.hold(t - 0.15)
            dfn.pose(t - 0.03, 'block', face=a)
            hit(t, mid, 0.8 * power, col, dust_n=3 if power > 1.2 else 0, wave=power > 1.2)
            dfn.pose(t + 0.16, 'block', loc=d + dv * kb * 0.6, z=1.72)
            dfn.later(t + 0.42, 'guard')
        elif res == 'dodge':
            perp = Vector((-dv.y, dv.x)) * side
            dfn.hold(t - 0.17)
            dfn.pose(t - 0.02, 'duck', loc=d + perp * 1.4, face=a)
            dfn.later(t + 0.3, 'guard')
        elif res == 'back':
            dfn.hold(t - 0.17)
            dfn.pose(t, 'guard', loc=(d.x + dv.x * 2.0, d.y + dv.y * 2.0, 2.7), face=a)
            dfn.pose(t + 0.17, 'land', loc=d + dv * 3.0)
            dfn.later(t + 0.42, 'guard')
        elif res == 'hit':
            dfn.hold(t - 0.05)
            hit(t, mid, 1.2 * power, col, dust_n=4)
            dfn.pose(t + 0.07, 'hit', loc=d + dv * 0.5, face=a)
            dfn.pose(t + 0.3, 'stagger', loc=d + dv * kb)
            dfn.later(t + 0.62, 'guard')
        elif res == 'catch':
            dfn.hold(t - 0.15)
            dfn.pose(t - 0.02, 'catch', face=a)
            hit(t, mid, 0.7 * power, col)
        elif res == 'launch':
            hit(t, mid, 1.6 * power, col, dust_n=6, wave=True)
        att.later(t + 0.2, move)
        att.later(t + 0.36, 'guard')
        return dv

    def fling(act, t, to, src, h=3.0, dur=0.6, end='lie'):
        p0, to = act.xy, V2(to)
        dv = unit(to - p0)
        act.pose(t, 'hit', face=src)
        m1, m2 = p0.lerp(to, 0.35), p0.lerp(to, 0.8)
        act.pose(t + dur * 0.3, 'fly', loc=(m1.x, m1.y, 2 + h), rx=-25)
        act.pose(t + dur * 0.72, 'fly', loc=(m2.x, m2.y, 2 + h * 0.7), rx=-55)
        tl = t + dur
        if end == 'lie':
            act.pose(tl, 'lie', loc=to)
            b1, b2 = to + dv * 0.9, to + dv * 1.6
            act.pose(tl + 0.13, 'lie', loc=(b1.x, b1.y, 1.1))
            act.pose(tl + 0.3, 'lie', loc=b2)
        else:
            act.pose(tl, 'land', loc=to, rx=0)
            act.pose(tl + 0.35, 'land', loc=to + dv * 1.6)
            Wd.dust(tl + 0.15, (to.x + dv.x, to.y + dv.y, 0), n=4, spread=2, size=1.4, seed=sd())
        Wd.dust(tl, (to.x, to.y, 0), n=6, spread=2.5, size=1.6, seed=sd())
        ev['land'].append(tl)
        ev['shakes'].append((tl, 5))
        return dv

    def dirto(act, name):
        return unit(V2(PIL[name]) - act.xy)

    def smash(act, t, name, end='lie', src=None):
        """Fling through a pillar that stands on the path."""
        p0 = act.xy
        pp = V2(PIL[name])
        dv = unit(pp - p0)
        to = pp + dv * 4.5
        dur = min(0.9, max(0.5, (to - p0).length / 24))
        k = (pp - p0).length / (to - p0).length
        fling(act, t, to, src if src is not None else p0 - dv, h=1.4, dur=dur, end=end)
        ts = t + dur * k
        Wd.shatter(name, ts, (dv.x, dv.y), power=13, seed=sd())
        ev['shatter'].append(ts)
        hit(ts, (pp.x, pp.y, 3.0), 1.3, dust_n=8, deb=12)

    def getup(act, t, face, dur=0.9, end='guard'):
        act.hold(t, bob=False)
        act.pose(t + dur * 0.5, 'kneel', face=face, rx=0)
        act.pose(t + dur, end)

    def jump(act, t0, t1, to, h=5.0, mid='air'):
        p0, to = act.xy, V2(to)
        act.hold(t0 - 0.16)
        act.pose(t0, 'antic', face=to, z=1.35)
        tm = (t0 + t1) / 2
        m = p0.lerp(to, 0.5)
        act.pose(tm, mid, loc=(m.x, m.y, 2 + h))
        ev['whoosh'].append(t0)

    def teleport(t, to, face):
        o = E.xy
        E.hold(t - 0.02, bob=False)
        E.pose(t + 0.03, 'idle', loc=to, face=face)
        Wd.impact(t, (o.x, o.y, 3), 1.0, (1.0, 0.1, 0.05))
        Wd.impact(t + 0.04, (to[0], to[1], 3), 1.0, (1.0, 0.1, 0.05))
        ev['teleport'].append(t)

    # ------------------------------------------------------------ hidden extras
    for k, act in enumerate((C, Dd, E)):
        act.pose(0, 'idle', loc=(70 + 3 * k, 80, -30), face=(0, 0))

    # ============================================================ 1. meeting 0-14
    A.pose(0, 'idle', loc=(-4.5, 0), face=(4.5, 0))
    B.pose(0, 'idle', loc=(4.5, 0), face=(-4.5, 0))
    A.hold(7.7)
    A.pose(8.2, 'tie')
    A.pose(8.6, 'tie', armR=(-74, 0, -58), head=(10, 0, 5))
    A.pose(9.0, 'tie')
    A.pose(9.5, 'idle', head=(-4, 0, 0))
    B.hold(9.7)
    B.pose(10.3, 'idle', head=(-14, 0, 0))
    B.pose(10.9, 'fists')
    A.hold(11.5)
    A.pose(12.0, 'guard')
    B.hold(11.9)
    B.pose(12.4, 'guard')
    A.hold(13.3)
    A.pose(13.58, 'antic', z=1.4)
    A.pose(13.82, 'dash', loc=(-0.5, 0))
    A.pose(14.0, 'punchR', loc=(1.9, 0))
    ev['whoosh'].append(13.7)
    for k in range(4):
        ev['step'].append(13.62 + k * 0.09)
    Wd.dust(13.62, (-4.5, 0, 0), n=5, spread=2, size=1.5, seed=sd())
    B.hold(13.8)
    B.pose(13.97, 'block')
    hit(14.02, (3.3, 0, 3.6), 1.5, dust_n=8, deb=10, wave=True)
    B.pose(14.4, 'block', loc=(7.2, 0), z=1.7)
    Wd.dust(14.2, (5.6, 0, 0), n=6, spread=2.5, size=1.6, seed=sd())
    A.later(14.2, 'punchR')
    A.later(14.5, 'guard')
    B.later(14.75, 'guard')

    # ============================================================ 2. the duel 14.5-40
    for (t, x, y, mv, rs, pw, sd_) in ((15.05, B, A, 'punchL', 'dodge', 1, 1), (15.45, A, B, 'punchR', 'block', 1, 1),
                                       (15.85, A, B, 'punchL', 'block', 1, 1), (16.3, B, A, 'kick', 'hit', 1, 1),
                                       (16.9, B, A, 'punchR', 'block', 1, 1), (17.3, B, A, 'punchL', 'dodge', 1, -1),
                                       (17.72, A, B, 'kick', 'hit', 1.1, 1)):
        strike(x, y, t, mv, rs, pw, side=sd_)
    dv = strike(A, B, 18.45, 'punchR', 'launch', 1.1, frm=dirto(B, 'P2'))
    smash(B, 18.47, 'P2')
    # B rises, both leap: air clash
    A.hold(19.2)
    run(A, 19.2, 19.9, (0.5, 0.5))
    getup(B, 19.3, A.xy, 0.6)
    run(B, 19.95, 20.2, (10.0, 2.0))
    mid = (A.xy + B.xy) / 2
    jump(A, 20.25, 20.75, toward(A.xy, mid, 1.3), h=6.0)
    jump(B, 20.25, 20.75, toward(B.xy, mid, 1.3), h=6.0)
    pa, pb = toward(A.xy, mid, 1.3), toward(B.xy, mid, 1.3)
    A.pose(20.75, 'airpunch', loc=(pa.x, pa.y, 8.4), face=mid)
    B.pose(20.75, 'airpunch', loc=(pb.x, pb.y, 8.4), face=mid)
    hit(20.78, (mid.x, mid.y, 9.9), 2.2, COLD)
    Wd.shockwave(20.78, (mid.x, mid.y, 9.9), r_end=16, dur=0.7, flat=False)
    la, lb = toward(A.xy, mid, 5.5), toward(B.xy, mid, 5.5)
    A.pose(21.05, 'fly', loc=((pa.x + la.x) / 2, (pa.y + la.y) / 2, 6.0))
    B.pose(21.05, 'fly', loc=((pb.x + lb.x) / 2, (pb.y + lb.y) / 2, 6.0))
    A.pose(21.3, 'land', loc=la)
    B.pose(21.3, 'land', loc=lb)
    for p in (la, lb):
        Wd.dust(21.3, (p.x, p.y, 0), n=7, spread=3, size=1.8, seed=sd())
        Wd.shockwave(21.3, (p.x, p.y, 0.1), r_end=6, dur=0.45)
    ev['land'] += [21.3, 21.32]
    ev['shakes'].append((21.3, 7))
    A.pose(21.7, 'guard')
    B.pose(21.7, 'guard')
    # run in, fists collide, struggle
    run(A, 21.85, 22.3, toward(A.xy, mid, 2.2))
    run(B, 21.85, 22.3, toward(B.xy, mid, 2.2))
    A.pose(22.42, 'punchR', loc=toward(A.xy, mid, 1.35), face=mid)
    B.pose(22.42, 'punchR', loc=toward(B.xy, mid, 1.35), face=mid)
    hit(22.44, (mid.x, mid.y, 3.7), 2.0, dust_n=8, deb=8, wave=True)
    Wd.cracks(22.44, (mid.x, mid.y), n=7, length=5, color=(1.0, 0.6, 0.25), seed=sd(), dur=0.25, width=0.12)
    for k in range(4):
        tt = 22.6 + k * 0.14
        s = 0.12 if k % 2 else -0.12
        A.pose(tt, 'punchR', loc=toward(A.xy, mid, 1.35 + s))
        B.pose(tt, 'punchR', loc=toward(B.xy, mid, 1.35 - s))
    strike(B, A, 23.4, 'kick', 'back')
    # flurry
    A.hold(23.9)
    k = 0
    t = 24.15
    order = [(A, B, 'punchR', 'block'), (B, A, 'punchL', 'block'), (A, B, 'punchL', 'dodge'), (B, A, 'punchR', 'block'),
             (A, B, 'kick', 'block'), (B, A, 'punchL', 'dodge'), (A, B, 'punchR', 'block'), (B, A, 'kick', 'block'),
             (A, B, 'punchL', 'hit')]
    for (x, y, mv, rs) in order:
        strike(x, y, t, mv, rs, 0.9, side=1 if k % 2 else -1, kb=0.8)
        t += 0.3
        k += 1
    # uppercut -> air slam
    t = 27.1
    dv = strike(A, B, t, 'punchR', 'launch', 1.2)
    bp = B.xy
    B.pose(t + 0.02, 'hit', face=A.xy)
    up = bp + dv * 2.0
    B.pose(t + 0.38, 'fly', loc=(up.x, up.y, 9.5), rx=-30)
    A.later(t + 0.14, 'punchR')
    A.pose(t + 0.24, 'antic', z=1.35)
    ev['whoosh'].append(t + 0.25)
    top = bp + dv * 1.0
    A.pose(t + 0.52, 'air', loc=(top.x, top.y, 12.5), face=up)
    A.pose(t + 0.7, 'slam', loc=(up.x - dv.x * 0.8, up.y - dv.y * 0.8, 10.6))
    hit(t + 0.72, (up.x, up.y, 10.4), 1.6, COLD)
    B.pose(t + 0.72, 'fly', loc=(up.x, up.y, 9.0), rx=-70)
    gp = bp + dv * 3.2
    B.pose(t + 0.92, 'lie', loc=gp)
    hit(t + 0.93, (gp.x, gp.y, 1.0), 2.3, dust_n=12, deb=18, wave=True)
    Wd.cracks(t + 0.93, (gp.x, gp.y), n=9, length=7, color=(1.0, 0.6, 0.25), seed=sd(), dur=0.3, width=0.14)
    B.pose(t + 1.05, 'lie', loc=(gp.x, gp.y, 1.2))
    B.pose(t + 1.22, 'lie', loc=gp)
    ap = gp - dv * 3.6
    A.pose(t + 1.1, 'land', loc=ap, face=gp)
    ev['land'].append(t + 1.1)
    A.pose(t + 1.6, 'idle')
    # A walks over, B catches the punch and kicks him through a pillar
    run(A, 28.9, 29.6, toward(A.xy, gp, 3.2), kind='walk')
    getup(B, 29.0, A.xy, 0.75)
    strike(A, B, 30.05, 'punchR', 'catch')
    strike(B, A, 30.5, 'punchL', 'hit', 1.1, kb=1.4)
    dv = strike(B, A, 31.0, 'kick', 'launch', 1.2, frm=dirto(A, 'P1'))
    smash(A, 31.02, 'P1')
    # second wind
    B.hold(31.9)
    getup(A, 32.3, B.xy, 1.1)
    run(B, 32.6, 33.5, (-1.0, 0.0))
    run(A, 33.42, 33.78, (-5.5, -0.6))
    strike(B, A, 34.0, 'punchR', 'dodge')
    for (t, x, y, mv, rs, pw) in ((34.4, A, B, 'kick', 'hit', 1.0), (35.0, B, A, 'punchR', 'block', 1.3),
                                  (35.4, A, B, 'punchL', 'hit', 1.0)):
        strike(x, y, t, mv, rs, pw)
    # cross-counter: both land a punch
    mid = (A.xy + B.xy) / 2
    A.hold(36.05)
    B.hold(36.05)
    for act, mv in ((A, 'punchR'), (B, 'punchL')):
        act.pose(36.2, 'antic', face=mid, z=1.6)
        act.pose(36.34, mv, loc=toward(act.xy, mid, 1.2), face=mid)
    ev['whoosh'] += [36.25, 36.27]
    hit(36.36, (mid.x, mid.y, 4.2), 2.2, dust_n=8, wave=True)
    for act in (A, B):
        act.pose(36.5, 'hit', loc=toward(act.xy, mid, 1.9))
        act.pose(36.95, 'stagger', loc=toward(act.xy, mid, 4.6))
        act.pose(37.4, 'pant', loc=toward(act.xy, mid, 5.0))
        Wd.dust(36.9, (act.loc.x, act.loc.y, 0), n=4, spread=2, size=1.4, seed=sd())
        act.hold(38.3)
        act.pose(38.7, 'guard')
    # last clash of the duel
    run(A, 38.9, 39.3, toward(A.xy, mid, 2.4))
    run(B, 38.9, 39.3, toward(B.xy, mid, 2.4))
    A.pose(39.42, 'punchR', loc=toward(A.xy, mid, 1.35), face=mid)
    B.pose(39.42, 'kick', loc=toward(B.xy, mid, 1.35), face=mid)
    hit(39.44, (mid.x, mid.y, 3.4), 2.4, COLD, dust_n=10, deb=10, wave=True)
    for act in (A, B):
        e1 = toward(act.xy, mid, 5.2)
        act.pose(39.62, 'hit', loc=toward(act.xy, mid, 2.5))
        act.pose(40.05, 'land', loc=e1)
        act.pose(40.3, 'land', loc=toward(act.xy, mid, 5.8))
        Wd.dust(39.9, (e1.x, e1.y, 0), n=5, spread=2.5, size=1.6, seed=sd())
        act.pose(40.8, 'guard')

    # ============================================================ 3. reinforcements 40-55
    bq = B.xy
    out = unit(bq - A.xy)
    side = Vector((-out.y, out.x))
    cl, dl = bq + out * 2.2 + side * 3.4, bq + out * 2.2 - side * 3.4
    for act, lp, t in ((C, cl, 41.0), (Dd, dl, 41.35)):
        hi = lp + out * 7
        act.hold(t - 0.5, bob=False)
        act.pose(t - 0.46, 'air', loc=(hi.x, hi.y, 17), face=A.xy)
        act.pose(t, 'land', loc=lp)
        Wd.dust(t, (lp.x, lp.y, 0), n=8, spread=3, size=2.0, seed=sd())
        Wd.shockwave(t, (lp.x, lp.y, 0.1), r_end=7, dur=0.5)
        Wd.cracks(t, (lp.x, lp.y), n=6, length=3, color=(0.5, 0.7, 1.0), seed=sd(), dur=0.2, width=0.1)
        ev['land'].append(t)
        ev['impacts'].append((t, 1.2))
        ev['shakes'].append((t, 8))
        act.pose(t + 0.6, 'idle')
    B.hold(41.2)
    B.pose(41.6, 'guard', head=(0, 0, 65))
    B.pose(42.3, 'guard', head=(0, 0, 65))
    B.pose(42.7, 'guard')
    C.hold(42.4)
    C.pose(42.9, 'guard', face=A.xy)
    Dd.hold(42.6)
    Dd.pose(43.1, 'fists', face=A.xy)
    A.hold(42.6)
    A.pose(43.0, 'idle', head=(-5, 0, 0))
    A.pose(43.6, 'tie')
    A.pose(44.1, 'guard')
    # team attack: C distracts, D from the side, B from above
    ap = A.xy
    run(C, 44.3, 44.95, toward(C.xy, ap, 3.6))
    strike(C, A, 45.15, 'punchR', 'block')
    strike(C, A, 45.55, 'punchL', 'dodge')
    strike(A, C, 45.95, 'punchR', 'block')
    ap = A.xy
    fl = ap + side * 6.0 + out * 1.0
    run(Dd, 44.3, 45.1, fl, step=0.16)
    run(Dd, 45.1, 45.9, toward(fl, ap, 4.0))
    dv = strike(Dd, A, 46.25, 'kick', 'hit', 1.3, kb=2.6)
    C.hold(46.2)
    tgt = A.xy
    jump(B, 45.6, 46.7, toward(B.xy, tgt, 1.5), h=10.0)
    B.pose(46.72, 'slam', loc=(tgt.x + out.x * 1.0, tgt.y + out.y * 1.0, 5.0), face=tgt)
    hit(46.78, (tgt.x, tgt.y, 2.2), 2.4, dust_n=12, deb=18, wave=True)
    Wd.cracks(46.78, (tgt.x, tgt.y), n=9, length=7, color=(1.0, 0.6, 0.25), seed=sd(), dur=0.3, width=0.14)
    A.pose(46.76, 'hit', face=B.xy)
    A.pose(46.86, 'lie', loc=tgt - out * 0.8)
    A.pose(47.0, 'lie', loc=(tgt.x - out.x * 1.6, tgt.y - out.y * 1.6, 1.3))
    A.pose(47.18, 'lie', loc=tgt - out * 2.4)
    B.pose(47.0, 'land', loc=tgt + out * 1.6)
    B.pose(47.5, 'guard')
    ev['land'].append(47.0)
    # A fights back against three
    getup(A, 47.9, B.xy, 0.8)
    C.hold(48.3)
    Dd.hold(48.3)
    run(C, 48.3, 48.75, toward(C.xy, A.xy, 3.4))
    strike(A, C, 49.05, 'kick', 'hit', 1.1, kb=2.2)
    run(Dd, 48.6, 49.1, toward(Dd.xy, A.xy, 3.4))
    strike(A, Dd, 49.45, 'punchR', 'block')
    strike(B, A, 49.85, 'punchL', 'hit', 1.0, kb=1.0)
    strike(Dd, A, 50.25, 'punchR', 'hit', 1.0, kb=1.0)
    dv = strike(C, A, 50.7, 'kick', 'launch', 1.2)
    fling(A, 50.72, A.xy + dv * 7.5, C.xy, h=2.2, dur=0.6)
    for act in (B, C, Dd):
        act.hold(51.3)
    getup(A, 51.7, B.xy, 1.2, end='pant')
    c0 = A.xy
    for i, act in enumerate((B, C, Dd)):
        o = (i - 1) * 2.6
        run(act, 51.5 + i * 0.1, 53.2, toward(act.xy, c0, 5.5) + Vector((-dv.y, dv.x)) * o, kind='walk')
        act.pose(53.6, 'guard', face=c0)
    A.hold(53.3)
    A.pose(53.8, 'guard')
    for act in (A, B, C, Dd):
        act.hold(55.3)

    # ============================================================ 4. the strongest 55-70
    by = 10.4
    boss0 = (0, 21.0)
    for i, act in enumerate((A, B, C, Dd)):
        t = 55.5 + i * 0.12
        act.pose(t + 0.35, 'guard', head=(0, 0, 40))
        act.pose(t + 0.9, 'guard', head=(0, 0, -35))
        act.pose(t + 1.5, 'idle', face=boss0, head=(-6, 0, 0))
        act.hold(62.6)
    Wd.smoke_cloud(55.4, 74.0, (0, 23), n=24, radius=7, color=(0.05, 0.022, 0.026), seed=12, rise=2.5)
    E.hold(57.3, bob=False)
    E.pose(57.35, 'walkA', loc=boss0, face=(0, 0))
    n = 13
    for i in range(1, n + 1):
        t = 57.35 + 0.76 * i
        y = boss0[1] - (boss0[1] - by) * i / n
        E.pose(t, 'walkB' if i % 2 else 'walkA', loc=(0, y), face=(0, 0))
        ev['bstep'].append(t)
        ev['shakes'].append((t, 3))
        if i >= 3:
            Wd.cracks(t, (0.5 if i % 2 else -0.5, y), n=5, length=2.6, seed=sd(), dur=0.2, width=0.1)
    E.pose(57.35 + 0.76 * n + 0.6, 'idle', loc=(0, by))
    Wd.cracks(60.4, (0, 16.5), n=11, length=15, seed=13, dur=1.2)
    ev['impacts'].append((60.4, 1.6))
    ev['shakes'].append((60.4, 12))
    Wd.aura(57.3, END_T, E.rig.root, n=40, seed=14)
    # the four line up - enemies a minute ago, now side by side
    line = [(-4.6, 0.6), (-1.6, -0.2), (1.6, -0.2), (4.6, 0.6)]
    for i, (act, p) in enumerate(zip((A, B, C, Dd), line)):
        run(act, 62.8 + i * 0.15, 65.4 + i * 0.15, p, kind='walk')
        act.pose(66.2 + i * 0.1, 'guard', face=(0, by))
        act.hold(69.8)
    E.hold(69.9)

    # ============================================================ 5. four against one 70-93
    bz = Vector((0, by))
    run(A, 70.0, 70.75, bz + Vector((-2.6, -3.2)))
    run(C, 70.05, 70.95, bz + Vector((-4.0, 0.6)))
    run(Dd, 70.05, 71.0, bz + Vector((4.0, 0.6)))
    run(B, 70.1, 71.0, bz + Vector((1.2, -6.0)))
    strike(A, E, 70.95, 'punchR', 'catch', col=RED)
    E.pose(71.12, 'punchL', face=A.xy)
    hit(71.13, (A.loc.x * 0.6, bz.y - 1.6, 3.7), 1.3, RED)
    fling(A, 71.14, A.xy + unit(A.xy - bz) * 6.5, bz, h=1.2, dur=0.5, end='land')
    for act, mv, t in ((C, 'punchR', 71.42), (Dd, 'punchL', 71.46)):
        act.hold(t - 0.24)
        act.pose(t - 0.12, 'antic', face=bz, z=1.6)
        act.pose(t, mv, loc=toward(act.xy, bz, 1.9), face=bz)
        ev['whoosh'].append(t - 0.1)
    E.pose(71.4, 'duck', face=(0, 0))
    E.pose(71.6, 'duck')
    E.pose(71.76, 'spread')
    hit(71.77, (bz.x, bz.y, 3.6), 2.0, RED, dust_n=8, wave=True)
    for act in (C, Dd):
        fling(act, 71.78, act.xy + unit(act.xy - bz) * 7.0, bz, h=1.6, dur=0.55, end='land')
    # B dives in - the boss is already behind him
    jump(B, 71.75, 72.25, bz, h=4.5)
    dw = unit(V2(PIL['W1']) - bz)
    teleport(72.12, bz - dw * 2.9, bz)
    B.pose(72.27, 'land', loc=bz, face=bz + Vector((0, 5)))
    Wd.dust(72.27, (bz.x, bz.y, 0), n=5, spread=2, size=1.5, seed=sd())
    ev['land'].append(72.27)
    B.pose(72.7, 'guard', head=(0, 0, 40))
    B.pose(73.0, 'guard', face=E.xy, head=(0, 0, 0))
    E.hold(72.95)
    dv = strike(E, B, 73.2, 'punchR', 'launch', 1.3, col=RED, frm=dw)
    smash(B, 73.22, 'W1')
    # three at once: he parries everything with one hand
    ez = E.xy
    for act, ang, t0 in ((A, 205, 73.3), (C, 335, 73.35), (Dd, 95, 73.4)):
        p = ez + Vector((math.cos(D(ang)), math.sin(D(ang)))) * 4.2
        act.pose(t0, 'guard', face=ez)
        run(act, t0 + 0.05, 73.85, p, face=ez)
    trio = (A, C, Dd)
    for k in range(9):
        strike(trio[k % 3], E, 74.05 + k * 0.2, ('punchR', 'punchL', 'kick')[(k // 3 + k) % 3], 'catch', 0.9, col=RED)
    E.pose(75.95, 'antic', z=1.7)
    E.pose(76.1, 'spread')
    hit(76.12, (ez.x, ez.y, 3.6), 2.4, RED, dust_n=10, deb=10, wave=True)
    Wd.shockwave(76.12, (ez.x, ez.y, 2.5), r_end=18, dur=0.6, color=(1.0, 0.2, 0.1))
    fling(A, 76.13, A.xy + unit(A.xy - ez) * 8, ez, h=2.5, dur=0.6)
    fling(C, 76.13, C.xy + unit(C.xy - ez) * 7, ez, h=2.5, dur=0.6)
    fling(Dd, 76.13, Dd.xy + unit(Dd.xy - ez) * 5.5, ez, h=1.4, dur=0.5, end='land')
    E.pose(76.7, 'idle')
    # D: kick -> he leans away, appears behind, one kick
    Dd.pose(76.95, 'guard')
    run(Dd, 77.0, 77.4, toward(Dd.xy, ez, 3.6))
    E.hold(77.45)
    Dd.pose(77.5, 'antic', z=1.6)
    Dd.pose(77.62, 'kick', loc=toward(Dd.xy, ez, 2.5), face=ez)
    ev['whoosh'].append(77.52)
    E.pose(77.6, 'duck', torso=(-25, 0, 0), z=1.9)
    dd = unit(Dd.xy - ez)
    teleport(77.85, Dd.xy + dd * 2.6, Dd.xy)
    Dd.later(77.95, 'guard')
    dv = strike(E, Dd, 78.12, 'kick', 'launch', 1.3, col=RED, reach=2.6)
    fling(Dd, 78.14, Dd.xy + dv * 12, E.xy, h=2.6, dur=0.7)
    # C from above: caught, held, thrown through a pillar
    getup(C, 77.3, E.xy, 0.8)
    ez = E.xy
    jump(C, 78.5, 79.1, toward(C.xy, ez, 1.4), h=7.0)
    cp = toward(C.xy, ez, 1.4)
    C.pose(79.1, 'slam', loc=(cp.x, cp.y, 5.6), face=ez)
    E.hold(78.85)
    E.pose(79.05, 'raise', face=cp, armR=(-160, 0, 0))
    hit(79.12, (ez.x * 0.6 + cp.x * 0.4, ez.y * 0.6 + cp.y * 0.4, 6.4), 1.3, RED)
    C.pose(79.3, 'hit', loc=(cp.x, cp.y, 5.2))
    C.pose(79.85, 'hit', loc=(cp.x, cp.y, 5.3), head=(-20, 0, 20))
    E.hold(79.8, bob=False)
    dv = unit(V2(PIL['P3']) - ez)
    E.pose(79.98, 'punchR', face=ez + dv * 5)
    ev['whoosh'].append(79.9)
    C.pose(80.0, 'hit', loc=(ez.x + dv.x * 2, ez.y + dv.y * 2, 3.0))
    smash(C, 80.02, 'P3', src=ez)
    E.later(80.5, 'idle')
    # A alone
    getup(A, 79.4, ez, 1.2, end='pant')
    A.hold(81.0)
    A.pose(81.3, 'guard', face=ez)
    run(A, 81.4, 81.95, toward(A.xy, ez, 3.4))
    strike(A, E, 82.15, 'punchR', 'dodge', side=1)
    strike(A, E, 82.55, 'punchL', 'dodge', side=-1)
    A.pose(82.83, 'antic', z=1.6, face=E.xy)
    A.pose(82.95, 'kick', loc=toward(A.xy, E.xy, 2.5), face=E.xy)
    ev['whoosh'].append(82.86)
    da = unit(A.xy - E.xy)
    teleport(82.9, A.xy + da * 2.8, A.xy)
    A.pose(83.25, 'guard', head=(0, 0, 50))
    A.pose(83.45, 'guard', face=E.xy)
    dv = strike(E, A, 83.62, 'punchL', 'launch', 1.2, col=RED)
    fling(A, 83.64, A.xy + dv * 8, E.xy, h=1.0, dur=0.5, end='land')
    A.pose(84.7, 'kneel')
    # B comes back; two together
    getup(B, 82.6, E.xy, 0.9)
    ez = E.xy
    run(B, 84.2, 85.1, toward(B.xy, ez, 4.2))
    A.hold(84.75)
    A.pose(84.95, 'guard', face=ez)
    run(A, 85.0, 85.3, toward(A.xy, ez, 4.0))
    strike(A, E, 85.5, 'punchR', 'block', 1.4, col=RED, kb=0.0)
    B.pose(85.42, 'antic', z=1.6, face=ez)
    B.pose(85.54, 'kick', loc=toward(B.xy, ez, 2.6), face=ez)
    hit(85.56, (ez.x, ez.y, 3.2), 1.2, RED)
    B.later(85.8, 'guard')
    strike(E, A, 85.95, 'punchR', 'hit', 1.3, kb=2.4, col=RED)
    strike(E, B, 86.35, 'kick', 'hit', 1.3, kb=2.4, col=RED)
    E.pose(86.72, 'antic', z=1.7)
    E.pose(86.86, 'spread')
    ez = E.xy
    hit(86.88, (ez.x, ez.y, 3.6), 2.4, RED, dust_n=10, deb=10, wave=True)
    Wd.shockwave(86.88, (ez.x, ez.y, 2.5), r_end=18, dur=0.6, color=(1.0, 0.2, 0.1))
    fling(A, 86.9, A.xy + unit(A.xy - ez) * 8, ez, h=2.5, dur=0.6)
    fling(B, 86.9, B.xy + unit(B.xy - ez) * 8, ez, h=2.5, dur=0.6)
    E.pose(87.5, 'idle')
    # everybody gets up for one last try
    for act, t in ((C, 87.3), (Dd, 87.5), (A, 88.0), (B, 88.2)):
        getup(act, t, ez, 1.0, end='pant')
    for i, act in enumerate((A, B, C, Dd)):
        act.hold(89.3)
        act.pose(89.6, 'guard', face=ez)
        ang = D(215 + i * 90 + 20)
        ring = ez + Vector((math.cos(ang), math.sin(ang))) * 6.0
        run(act, 89.65, 90.3, ring, face=ez)
        near = ez + Vector((math.cos(ang), math.sin(ang))) * 1.3
        jump(act, 90.35, 90.75, near, h=3.5)
        act.pose(90.75, 'airpunch', loc=(near.x, near.y, 5.2), face=ez)
    E.hold(90.55)
    teleport(90.62, (ez.x, ez.y), (0, 0))
    E.pose(90.68, 'float', loc=(ez.x, ez.y, 13.5))
    hit(90.78, (ez.x, ez.y, 6.6), 1.4, COLD)
    E.pose(90.95, 'float', loc=(ez.x, ez.y, 13.8))
    E.pose(91.12, 'slam', loc=(ez.x, ez.y, 8.0))
    ev['whoosh'].append(91.0)
    E.pose(91.25, 'land', loc=ez)
    hit(91.27, (ez.x, ez.y, 1.2), 3.0, RED, dust_n=14, deb=26, wave=True)
    Wd.cracks(91.27, (ez.x, ez.y), n=12, length=13, seed=sd(), dur=0.5, width=0.2)
    Wd.shockwave(91.27, (ez.x, ez.y, 0.3), r_end=30, dur=0.9, color=(1.0, 0.15, 0.05), strength=14)
    for i, act in enumerate((A, B, C, Dd)):
        p = act.xy
        act.pose(91.0, 'hit', loc=(p.x, p.y, 4.6))
        act.pose(91.25, 'hit', loc=(p.x, p.y, 2.6))
        fling(act, 91.3, p + unit(p - ez) * (6.5 + i * 0.5), ez, h=3.0, dur=0.7)
    E.pose(92.0, 'land')
    E.pose(92.8, 'idle', face=(ez.x, ez.y - 10))

    # ============================================================ 6. finale 93-105.5
    for i, act in enumerate((A, B, C, Dd)):
        act.hold(93.4 + i * 0.2, bob=False)
        act.pose(94.3 + i * 0.2, 'kneel', face=ez, rx=0)
        act.hold(97.5)
    E.hold(95.2)
    E.pose(96.3, 'raise')
    E.hold(97.5)
    hand = (ez.x, ez.y, 7.4)
    # charge: a small sun grows over his hand
    m, fade = Wd.fx_mat((1.0, 0.12, 0.05), 30)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=hand)
    orb = bpy.context.object
    orb.name = 'fx_orb'
    orb.data.materials.append(m)
    Wd.key_scale(orb, [(F(95.6) - 1, 0.01), (F(95.6), 0.1), (F(97.4), 1.1), (F(97.5), 0.01)])
    Wd.key_fade(fade, [(F(95.6) - 1, 0), (F(95.6), 1), (F(97.5), 1), (F(97.5) + 1, 0)])
    bpy.ops.object.light_add(type='POINT', location=hand)
    L = bpy.context.object
    L.data.color = (1.0, 0.15, 0.06)
    for t, e in ((95.6, 0), (97.4, 30000), (97.6, 0)):
        L.data.energy = e
        L.data.keyframe_insert('energy', frame=F(t))
    for k in range(5):
        Wd.shockwave(95.9 + k * 0.32, (ez.x, ez.y, 0.2), r_end=9, dur=0.45, color=(1.0, 0.15, 0.05), strength=8)
    Wd.energy_sphere(97.5, 99.3, hand, r_end=60)
    Wd.shockwave(97.5, (ez.x, ez.y, 0.2), r_end=45, dur=1.3, color=(1.0, 0.15, 0.05), strength=14)
    Wd.cracks(97.5, (ez.x, ez.y), n=14, length=26, seed=25, dur=0.8, width=0.3)
    Wd.dust(97.6, (ez.x, ez.y, 0), n=12, spread=12, size=3, dur=3.0, seed=sd())
    ev['impacts'].append((97.5, 3.0))
    ev['shakes'].append((97.5, 26))
    for i, act in enumerate((A, B, C, Dd)):
        p = act.xy
        fling(act, 97.62 + i * 0.03, p + unit(p - ez) * 4.0, ez, h=3.2, dur=0.8)
    E.hold(99.8, bob=False)
    E.pose(100.9, 'idle')
    E.hold(102.6)
    E.pose(103.4, 'idle', head=(6, 0, 0), torso=(3, 0, 0))
    E.hold(END_T + 0.1)
    for act in (A, B, C, Dd):
        act.hold(END_T + 0.1)
    # eyes flare on the last look
    gm = bpy.data.materials.get('boss_glow')
    if gm:
        s = gm.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
        for t, v in ((102.8, 25), (103.6, 90), (END_T, 120)):
            s.default_value = v
            s.keyframe_insert('default_value', frame=F(t))
    return ez


# =============================================================== cameras
_ncam = [0]


def shot(t0, t1, keys, lens=30, fstop=3.5):
    """keys: [(t, cam_pos, look_at)]. One camera object per shot, bound with a timeline marker."""
    sc = bpy.context.scene
    _ncam[0] += 1
    cd = bpy.data.cameras.new('cam%d' % _ncam[0])
    cam = bpy.data.objects.new('cam%d' % _ncam[0], cd)
    sc.collection.objects.link(cam)
    tgt = bpy.data.objects.new('camt%d' % _ncam[0], None)
    sc.collection.objects.link(tgt)
    con = cam.constraints.new('TRACK_TO')
    con.target = tgt
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    cd.dof.use_dof = True
    cd.dof.focus_object = tgt
    cd.dof.aperture_fstop = fstop
    cd.sensor_fit = 'VERTICAL'
    cd.sensor_height = 24
    cd.lens = lens
    cd.clip_end = 500
    for t, p, l in keys:
        rr = math.hypot(p[0], p[1])
        if rr > 24 and t0 > 5:
            p = (p[0] * 24 / rr, p[1] * 24 / rr, p[2])
        cam.location = (p[0], p[1], max(0.35, p[2]))
        cam.keyframe_insert('location', frame=F(t))
        tgt.location = l
        tgt.keyframe_insert('location', frame=F(t))
    m = sc.timeline_markers.new('c%d' % _ncam[0], frame=F(t0))
    m.camera = cam
    if _ncam[0] == 1:
        sc.camera = cam
    EVENTS['cuts'].append(t0)


def cameras(c, ez):
    A, B, C, Dd, E = c['suit'], c['emo'], c['mask'], c['blue'], c['boss']

    def st(t0, t1, p0, p1, l0, l1, lens=30, fstop=3.5):
        shot(t0, t1, [(t0, p0, l0), (t1, p1, l1)], lens, fstop)

    def duel(t0, t1, X, Y, ang0, ang1, dist=15, h=3.0, lens=26, fstop=4.0, lz=3.3, dist1=None, h1=None):
        """Orbit around the midpoint of two fighters. ang = degrees off the X->Y axis."""
        a0, b0 = X.sm((t0 + t1) / 2, 0.6), Y.sm((t0 + t1) / 2, 0.6)
        base = math.atan2(b0.y - a0.y, b0.x - a0.x)
        keys = []
        n = max(2, int((t1 - t0) / 0.3) + 1)
        for k in range(n):
            f = k / (n - 1)
            t = t0 + (t1 - t0) * f
            a, b = X.sm(t), Y.sm(t)
            mid = (a + b) / 2
            ang = base + D(ang0 + (ang1 - ang0) * f)
            dd = 1.35 * (dist + ((dist1 if dist1 is not None else dist) - dist) * f)
            hh = h + ((h1 if h1 is not None else h) - h) * f
            keys.append((t, (mid.x + math.cos(ang) * dd, mid.y + math.sin(ang) * dd, hh),
                         (mid.x, mid.y, lz + max(0, mid.z - 2.0) * 0.8)))
        shot(t0, t1, keys, lens, fstop)

    def track(t0, t1, X, off0, off1, lens=35, fstop=2.5, lz=4.4, w=0.3):
        keys = []
        n = max(2, int((t1 - t0) / 0.25) + 1)
        for k in range(n):
            f = k / (n - 1)
            t = t0 + (t1 - t0) * f
            p = X.sm(t, w)
            o = Vector(off0).lerp(Vector(off1), f)
            keys.append((t, (p.x + o.x, p.y + o.y, o.z), (p.x, p.y, p.z - 2.0 + lz)))
        shot(t0, t1, keys, lens, fstop)

    # ---- 1 meeting
    shot(0.0, 5.6, [(0.0, (3, -92, 20), (0, -40, 9)), (2.0, (-2.5, -64, 9), (0, -20, 5)),
                    (4.0, (2, -38, 4.5), (0, 0, 4)), (5.6, (0, -20, 3.2), (0, 0, 3.4))], 24, 5.0)
    duel(5.6, 7.6, A, B, -125, -110, dist=15, h=1.6)
    track(7.6, 9.6, A, (6.0, -5.5, 4.3), (5.0, -5.0, 4.6), lens=45, fstop=2.0)
    track(9.6, 11.4, B, (-6.0, -5.5, 3.8), (-5.0, -5.0, 4.5), lens=45, fstop=2.0)
    duel(11.4, 13.3, A, B, 172, 165, dist=13, h=3.0, lens=32, fstop=3.0)
    duel(13.3, 14.6, A, B, -60, -40, dist=13, h=2.2, lens=24)
    # ---- 2 duel
    duel(14.6, 16.6, A, B, -65, -25, dist=14, h=2.6)
    duel(16.6, 18.3, A, B, 150, 115, dist=13, h=3.4)
    track(18.3, 19.3, B, (-3, -17, 2.2), (2, -16, 2.6), lens=24, fstop=5, lz=3.2)
    duel(19.3, 20.25, A, B, -80, -70, dist=14, h=1.4)
    duel(20.25, 21.5, A, B, -78, -60, dist=15, h=1.0, lens=22, lz=3.2)
    duel(21.5, 23.2, A, B, -35, 10, dist=11, h=2.4)
    duel(23.2, 25.6, A, B, 100, 40, dist=11, h=3.6)
    duel(25.6, 27.0, A, B, -30, -70, dist=10, h=2.2)
    duel(27.0, 28.3, A, B, -85, -70, dist=16, h=1.2, lens=22, lz=3.4)
    track(28.3, 29.6, B, (4.0, -8.0, 0.9), (5.0, -7.0, 1.4), lens=30, fstop=2.2, lz=2.4)
    duel(29.6, 31.0, A, B, 60, 80, dist=12, h=3.0)
    track(31.0, 32.3, A, (4, -17, 2.4), (-2, -15, 2.0), lens=24, fstop=5, lz=3.0)
    track(32.3, 33.5, A, (4.0, -7.5, 1.6), (2.5, -7.0, 3.4), lens=35, fstop=2.0, lz=3.6)
    duel(33.5, 36.0, A, B, -50, -110, dist=12, h=2.8)
    duel(36.0, 37.5, A, B, -88, -84, dist=12, h=2.2)
    duel(37.5, 38.8, A, B, 25, 15, dist=14, h=3.6, lens=40, fstop=2.2, lz=4.0)
    duel(38.8, 40.6, A, B, -75, -55, dist=14, h=1.6, lens=24)
    # ---- 3 reinforcements
    duel(40.6, 42.4, A, B, 155, 165, dist=13, h=1.5, lens=24, lz=4.0)
    duel(42.4, 43.2, C, Dd, 100, 95, dist=10, h=3.0, lens=30, lz=3.8)
    bq = B.sm(43.7)
    aq = A.sm(43.7)
    out = unit(Vector((bq.x - aq.x, bq.y - aq.y)))
    sd = Vector((-out.y, out.x))
    track(43.2, 44.3, A, tuple(out * 7.5 + sd * 2.5) + (3.8,), tuple(out * 6.5 + sd * 2.0) + (4.4,), lens=42,
          fstop=2.0, lz=4.5)
    duel(44.3, 46.1, A, C, -60, -100, dist=13, h=3.0)
    duel(46.1, 47.4, A, B, -80, -65, dist=15, h=1.2, lens=22, lz=3.6)
    track(47.4, 48.3, A, (-2.5, -8.5, 0.9), (-3.5, -7.5, 1.6), lens=30, fstop=2.2, lz=2.6)
    duel(48.3, 50.6, A, B, -70, -20, dist=13, h=3.2, lens=24)
    track(50.6, 51.7, A, (3, -15, 2.0), (0, -14, 2.2), lens=24, fstop=5, lz=3.0)
    duel(51.7, 53.4, A, B, 125, 105, dist=12, h=1.4, lens=24)
    duel(53.4, 55.0, A, B, 25, 35, dist=13, h=3.2, lens=28)
    # ---- 4 the strongest
    g = (A.sm(58).xy + B.sm(58).xy + C.sm(58).xy + Dd.sm(58).xy) / 4
    st(55.0, 56.6, (g.x * 0.1 + 4, g.y * 0.1 + 6, 9.0), (g.x * 0.1 + 2, g.y * 0.1 + 3, 7.0), (g.x, g.y, 3.2), (g.x, g.y, 3.2), 24, 5.0)
    st(56.6, 58.2, (g.x + 4, g.y + 15, 3.0), (g.x + 3, g.y + 13.5, 3.4), (g.x, g.y, 3.6), (g.x, g.y, 3.8), 30, 3.0)
    st(58.2, 60.3, (g.x * 0.3 + 2, g.y - 6, 6.5), (g.x * 0.2 + 1.5, g.y - 3, 6.0), (0, 21, 4.5), (0, 19, 4.6), 85, 4.0)
    track(60.3, 62.6, E, (4.5, -10.0, 0.6), (3.8, -9.0, 0.8), lens=28, fstop=2.2, lz=1.0)
    track(62.6, 64.6, E, (-1.8, -8.0, 3.4), (-1.2, -7.2, 4.0), lens=45, fstop=2.0, lz=4.5)
    st(64.6, 66.4, (-8, 10.5, 4.2), (4, 10.5, 4.3), (-4.6, 0.6, 4.4), (4.6, 0.6, 4.4), 40, 2.0)
    st(66.4, 68.2, (1.0, 4.4, 4.6), (0.7, 5.8, 4.65), (0, 10.4, 4.7), (0, 10.4, 4.7), 55, 1.6)
    st(68.2, 70.0, (3.8, 17.0, 5.6), (3.2, 16.2, 5.2), (0, 2, 2.8), (0, 2, 2.8), 26, 5.0)
    # ---- 5 four against one
    st(70.0, 71.0, (10, -7, 2.2), (9, -3, 2.8), (0, 4, 3.2), (0, 9, 3.4), 24, 4.0)
    st(71.0, 72.1, (8, 0.5, 2.4), (7, 0.0, 3.2), (0, 10.2, 3.5), (0, 10.2, 3.6), 26, 4.0)
    st(72.1, 73.1, (5.0, 20.0, 3.0), (4.2, 19.0, 3.4), (-0.6, 9.6, 3.6), (-0.8, 9.4, 3.6), 28, 3.0)
    track(73.1, 74.0, B, (-10, -9, 2.2), (-9, -10, 3.0), lens=24, fstop=5, lz=3.2)
    ez1 = E.sm(75.0)
    shot(74.0, 76.0, [(74.0 + k * 0.25, (ez1.x + math.cos(D(250 + k * 14)) * 14, ez1.y + math.sin(D(250 + k * 14)) * 14,
                                         2.4 + k * 0.2), (ez1.x, ez1.y, 3.5)) for k in range(9)], 26, 4.0)
    st(76.0, 77.0, (ez1.x + 2, ez1.y - 19, 5.0), (ez1.x + 1, ez1.y - 18, 4.0), (ez1.x, ez1.y, 3.6),
       (ez1.x, ez1.y, 3.4), 24, 5.0)
    duel(77.0, 78.9, E, Dd, -60, -95, dist=12, h=2.6)
    duel(78.9, 80.0, E, C, -70, -80, dist=12, h=1.4, lz=4.6)
    e80 = E.sm(80.4)
    st(80.0, 80.9, (e80.x + 4.5, e80.y - 5.5, 3.0), (e80.x + 4.0, e80.y - 5.0, 3.4), (e80.x - 3, e80.y + 1, 3.4),
       (PIL['P3'][0], PIL['P3'][1], 3.4), 24, 5.0)
    track(80.9, 81.9, A, (3.5, -7.5, 2.8), (2.0, -7.0, 3.8), lens=40, fstop=2.0, lz=4.2)
    duel(81.9, 83.5, A, E, -55, -100, dist=11, h=2.8)
    duel(83.5, 84.8, A, E, -100, -85, dist=13, h=1.6, lens=24)
    duel(84.8, 87.6, A, E, 70, 130, dist=12, h=3.4, lens=24, lz=3.4)
    ez2 = E.sm(89.0)
    st(87.6, 89.6, (ez2.x - 5, ez2.y - 21, 10.0), (ez2.x - 2, ez2.y - 19, 8.0), (ez2.x, ez2.y, 2.6),
       (ez2.x, ez2.y, 3.0), 26, 6.0)
    shot(89.6, 92.0, [(89.6, (ez2.x + 9, ez2.y - 15, 1.2), (ez2.x, ez2.y, 3.4)),
                      (90.6, (ez2.x + 7, ez2.y - 16, 1.0), (ez2.x, ez2.y, 5.0)),
                      (91.0, (ez2.x + 6, ez2.y - 17, 1.0), (ez2.x, ez2.y, 8.0)),
                      (91.3, (ez2.x + 6, ez2.y - 17.5, 1.2), (ez2.x, ez2.y, 3.0)),
                      (92.0, (ez2.x + 5, ez2.y - 18.5, 1.6), (ez2.x, ez2.y, 3.2))], 22, 5.0)
    # ---- 6 finale
    st(92.0, 93.6, (ez.x + 2.2, ez.y - 8.5, 1.2), (ez.x + 1.4, ez.y - 8.0, 2.2), (ez.x, ez.y, 3.2), (ez.x, ez.y, 4.0),
       30, 2.4)
    a94 = A.sm(95.0)
    ao = unit(Vector((a94.x - ez.x, a94.y - ez.y)))
    q = Vector((a94.x, a94.y)) + ao * 8 + Vector((-ao.y, ao.x)) * 2.0
    st(93.6, 95.4, (q.x, q.y, 1.0), (q.x - ao.x, q.y - ao.y, 1.4), (a94.x, a94.y, 2.2), (ez.x, ez.y, 3.6), 28, 3.0)
    st(95.4, 97.5, (ez.x - 3.2, ez.y - 9.5, 1.0), (ez.x - 2.2, ez.y - 8.0, 0.8), (ez.x, ez.y, 4.6), (ez.x, ez.y, 6.0),
       26, 4.0)
    st(97.5, 100.6, (ez.x + 5, ez.y - 17, 3.0), (ez.x + 3, ez.y - 22, 6.5), (ez.x, ez.y, 4.6), (ez.x, ez.y, 3.6),
       24, 6.0)
    st(100.6, END_T + 0.1, (ez.x, ez.y - 12.0, 4.2), (ez.x, ez.y - 4.8, 4.5), (ez.x, ez.y, 4.5), (ez.x, ez.y, 4.56),
       50, 1.8)


# =============================================================== world, lighting
def street():
    """Two rows of ruined blocks leading to the arena (the opening fly-through)."""
    r = random.Random(9)
    conc = chars.mat('concrete', chars.hexrgb('#2a2d33'), 0.9)
    conc2 = chars.mat('concrete2', chars.hexrgb('#1d2026'), 0.9)
    win = chars.mat('win_off', (0.01, 0.01, 0.012), 0.3)
    won = chars.mat('win_on', (0.3, 0.2, 0.08), 0.5, emit=(1.0, 0.62, 0.3), emit_strength=3)
    for sx in (-1, 1):
        y = -100.0
        while y < -30:
            w, dp, h = r.uniform(9, 13), r.uniform(9, 14), r.uniform(14, 34)
            x = sx * (9.5 + w / 2 + r.uniform(0, 3))
            b = chars.box('st%d_%d' % (sx, int(-y)), (w, dp, h), (0, 0, h / 2), conc if r.random() < 0.5 else conc2,
                          bevel=0.0)
            b.location = (x, y + dp / 2, 0)
            b.rotation_euler = (0, 0, r.uniform(-0.08, 0.08))
            for k in range(2):
                cck = chars.box('stc%d_%d_%d' % (sx, int(-y), k), (r.uniform(2, w * 0.6), r.uniform(2, dp * 0.6),
                                                                   r.uniform(1, 5)),
                                (r.uniform(-w / 3, w / 3), r.uniform(-dp / 3, dp / 3), h + r.uniform(0, 2)), conc2,
                                bevel=0.0)
                cck.parent = b
                cck.rotation_euler = (r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), 0)
            for rr in range(int(h / 4)):
                for cc in range(int(dp / 3)):
                    if r.random() < 0.45:
                        continue
                    wb = chars.box('stw', (0.2, 1.2, 1.8), (-sx * (w / 2 + 0.05), -dp / 2 + 1.8 + cc * 3, 2.5 + rr * 4),
                                   won if r.random() < 0.1 else win, bevel=0.0)
                    wb.parent = b
            y += dp + r.uniform(1.5, 5)
    rub = chars.mat('rubble', chars.hexrgb('#34373d'), 0.95)
    for i in range(40):
        s = r.uniform(0.4, 1.8)
        b = chars.box('strub%d' % i, (s, s * r.uniform(0.5, 1.2), s * r.uniform(0.3, 0.9)), (0, 0, 0), rub, bevel=0.04)
        b.location = (r.choice((-1, 1)) * r.uniform(4.5, 9), r.uniform(-95, -22), s * 0.25)
        b.rotation_euler = (r.uniform(-0.4, 0.4), r.uniform(-0.4, 0.4), r.uniform(0, 3))


PIL = {'P2': (14.0, 3.0), 'P1': (-14.0, -2.0), 'W1': (10.0, 20.0), 'P3': (-13.0, 17.0)}


def soft_smoke_mat(color, name=None):
    """Self-lit puff with soft edges (alpha falls off towards the silhouette); 'fade' is keyframed."""
    m = bpy.data.materials.new(name or Wd._fxname('smoke'))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (color[0] * 0.6, color[1] * 0.6, color[2] * 0.6, 1)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    val = nt.nodes.new('ShaderNodeValue')
    val.name = 'fade'
    val.outputs[0].default_value = 0.0
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    inv = nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    pw = nt.nodes.new('ShaderNodeMath')
    pw.operation = 'POWER'
    pw.inputs[1].default_value = 2.0
    mul = nt.nodes.new('ShaderNodeMath')
    mul.operation = 'MULTIPLY'
    L = nt.links
    L.new(lw.outputs['Facing'], inv.inputs[1])
    L.new(inv.outputs[0], pw.inputs[0])
    L.new(pw.outputs[0], mul.inputs[0])
    L.new(val.outputs[0], mul.inputs[1])
    L.new(mul.outputs[0], mix.inputs[0])
    L.new(tr.outputs[0], mix.inputs[1])
    L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    return m, val.outputs[0]


Wd.smoke_mat = soft_smoke_mat


def prep_world():
    # clear the ring blocks that close the street, and the lamp that stands where the boss walks in
    kill = []
    for ob in bpy.data.objects:
        if ob.name.startswith('bld') and ob.parent is None and abs(ob.location.x) < 24 and ob.location.y < -20:
            kill.append(ob)
        if ob.name.startswith('rub') and ob.location.length < 21:
            kill.append(ob)
        if ob.name in ('lamp4', 'lampL4'):
            kill.append(ob)
    for ob in kill:
        for ch in list(ob.children_recursive):
            bpy.data.objects.remove(ch, do_unlink=True)
        if ob in Wd.LAMPS:
            Wd.LAMPS.remove(ob)
        bpy.data.objects.remove(ob, do_unlink=True)
    for i, y in enumerate((-78, -52, -30)):
        bpy.ops.object.light_add(type='POINT', location=((-1) ** i * 6, y, 7))
        L = bpy.context.object
        L.data.energy = 9000
        L.data.color = (1.0, 0.62, 0.32)
        L.data.shadow_soft_size = 1.0
    # wet asphalt: glossy puddles + fine bump, and worn road markings like a real street
    am = bpy.data.materials['asphalt']
    nt = am.node_tree
    pb = nt.nodes['Principled BSDF']
    for n in nt.nodes:
        if n.type == 'MAP_RANGE':
            n.inputs['To Min'].default_value = 0.04
            n.inputs['To Max'].default_value = 0.6
    n2 = nt.nodes.new('ShaderNodeTexNoise')
    n2.inputs['Scale'].default_value = 60
    n2.inputs['Detail'].default_value = 6
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.35
    bump.inputs['Distance'].default_value = 0.05
    nt.links.new(n2.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], pb.inputs['Normal'])
    paint = chars.mat('roadpaint', (0.55, 0.55, 0.5), 0.35)
    y = -96.0
    while y < 26:
        d = chars.box('dash', (0.35, 3.2, 0.02), (0, 0, 0.012), paint, bevel=0.0)
        d.location = (0.6, y, 0)
        y += 6.5
    for sx in (-1, 1):
        ln = chars.box('edge', (0.25, 80, 0.02), (0, 0, 0.012), paint, bevel=0.0)
        ln.location = (sx * 8.2, -62, 0)
    for name, p in PIL.items():
        Wd.pillar(name, p, size=(2.6, 2.6, 9), grid=(2, 2, 6))


def lighting(c):
    sc = bpy.context.scene
    T = T_BOSS
    w = bpy.data.worlds.new('night')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.02, 0.03, 0.055, 1)
    bg.inputs[1].default_value = 1.0
    bpy.ops.object.light_add(type='SUN', rotation=(D(58), 0, D(205)))
    moon = bpy.context.object
    moon.data.color = (0.55, 0.68, 1.0)
    moon.data.angle = D(2)
    bpy.ops.object.light_add(type='AREA', location=(0, -8, 18))
    fill = bpy.context.object
    fill.data.size = 24
    fill.data.color = (0.5, 0.6, 0.9)
    tgt = bpy.data.objects.new('rim_tgt', None)
    bpy.context.collection.objects.link(tgt)
    tgt.location = (0, 2, 2)

    def spot(loc, energy, color, size):
        bpy.ops.object.light_add(type='SPOT', location=loc)
        L = bpy.context.object
        L.data.energy = energy
        L.data.color = color
        L.data.spot_size = D(size)
        L.data.spot_blend = 0.8
        L.data.shadow_soft_size = 2
        con = L.constraints.new('TRACK_TO')
        con.target = tgt
        con.track_axis = 'TRACK_NEGATIVE_Z'
        con.up_axis = 'UP_Y'
        return L
    rim = spot((0, 30, 16), 170000, (0.55, 0.75, 1.0), 75)
    rim2 = spot((-24, -8, 11), 80000, (1.0, 0.62, 0.35), 65)
    rim3 = spot((24, -10, 12), 70000, (0.5, 0.72, 1.0), 65)
    for ob, a, b in ((moon, 3.5, 2.2), (fill, 2600, 1800), (rim, 170000, 70000), (rim2, 80000, 30000),
                     (rim3, 70000, 40000)):
        for t, e in ((T + 0.6, a), (T + 2.0, b)):
            ob.data.energy = e
            ob.data.keyframe_insert('energy', frame=F(t))
    # the boss carries his own red backlight
    E = c['boss']
    bpy.ops.object.light_add(type='POINT', location=(0, 4.5, 4.5))
    red = bpy.context.object
    red.parent = E.rig.root
    red.data.color = (1.0, 0.08, 0.04)
    red.data.shadow_soft_size = 2.5
    for t, e in ((T + 2.3, 0), (T + 3.2, 9000), (END_T, 9000)):
        red.data.energy = e
        red.data.keyframe_insert('energy', frame=F(t))
    bpy.ops.object.light_add(type='POINT', location=(1.5, -5.0, 3.6))
    key = bpy.context.object                       # soft cold key so his face reads in the close-ups
    key.parent = E.rig.root
    key.data.color = (0.7, 0.8, 1.0)
    key.data.shadow_soft_size = 2.0
    for t, e in ((T + 2.3, 0), (T + 4, 500), (100.0, 500), (102.5, 900)):
        key.data.energy = e
        key.data.keyframe_insert('energy', frame=F(t))
    for i, L in enumerate(Wd.LAMPS):
        for t, e in ((T, 6000), (T + 0.2, 800), (T + 0.3, 6000), (T + 0.5, 400), (T + 0.6, 4000), (T + 0.9, 300),
                     (T + 1.1, 3000), (T + 1.5, 0)):
            L.data.energy = e
            L.data.keyframe_insert('energy', frame=F(t + i * 0.05))
    Wd.key_fog(T, (0.045, 0.06, 0.09), 0.012)
    Wd.key_fog(T + 2.5, (0.09, 0.025, 0.03), 0.015)


def render_settings():
    sc = bpy.context.scene
    res = tuple(int(v) for v in os.environ.get('RES', '540x960').split('x'))
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = int(os.environ.get('SAMPLES', 6))
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = float(os.environ.get('ATH', 0.1))
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.cycles.diffuse_bounces = 1
    sc.cycles.glossy_bounces = 1
    sc.cycles.transparent_max_bounces = 48
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.use_motion_blur = os.environ.get('MB', '1') == '1'
    sc.render.motion_blur_shutter = 0.5
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.render.use_persistent_data = True
    if os.environ.get('THREADS'):
        sc.render.threads_mode = 'FIXED'
        sc.render.threads = int(os.environ['THREADS'])
    sc.render.image_settings.file_format = 'PNG'
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Punchy'
    except Exception:
        pass
    sc.view_settings.exposure = 1.0
    sc.frame_start, sc.frame_end = 1, F(END_T)


def build():
    Wd.ground()
    Wd.buildings()
    street()
    Wd.debris_field()
    Wd.lamps()
    prep_world()
    cast = build_cast()
    ez = choreography(cast)
    for a in cast.values():
        a.flush(1e9)
    for tt in (14.5, 19, 21.5, 27, 31, 33, 36, 40.5, 44, 47, 51, 55, 66, 73, 77, 81, 87, 92, 99):
        print('POS', tt, *[tuple(round(v, 1) for v in cast[k].at(tt)) for k in ('suit', 'emo', 'mask', 'blue', 'boss')])
    cameras(cast, ez)
    lighting(cast)
    Wd.apply_fog()
    render_settings()
    EVENTS['cuts'].sort()
    json.dump(EVENTS, open(os.path.join(HERE, 'events2.json'), 'w'), indent=1)
    return cast


if __name__ == '__main__':
    build()
    sc = bpy.context.scene
    args = sys.argv[1:]
    mode = args[0] if args else 'still'
    if mode == 'render':
        a, b = int(args[1]), int(args[2])
        step = int(args[3]) if len(args) > 3 else 1
        out = os.path.join(HERE, os.environ.get('OUT', 'frames2'))
        os.makedirs(out, exist_ok=True)
        import time
        for fr in range(a, b + 1, step):
            fp = os.path.join(out, '%04d.png' % fr)
            if os.path.exists(fp):
                continue
            open(fp, 'wb').close()                 # claim, so parallel workers skip it
            sc.frame_set(fr)
            sc.render.filepath = fp
            t = time.time()
            bpy.ops.render.render(write_still=True)
            print('FRAME', fr, round(time.time() - t, 1), flush=True)
    else:
        import time
        for fr in args[1:]:
            sc.frame_set(int(fr))
            sc.render.filepath = os.path.join(HERE, 'stills', 'f%04d.png' % int(fr))
            t = time.time()
            bpy.ops.render.render(write_still=True)
            print('STILL', fr, round(time.time() - t, 1), flush=True)
