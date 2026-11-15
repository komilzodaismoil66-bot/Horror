"""Roblox-style cinematic short (~30 s, 9:16), built and rendered with Blender (bpy, Cycles CPU).

python3 film.py render START END      render frames START..END to frames/####.png
python3 film.py still FRAME [FRAME..] render single frames (for checks)
"""
import json
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
import chars
import world as Wd
from world import F, FPS

HERE = os.path.dirname(os.path.abspath(__file__))
D = math.radians
END_T = 28.2                       # last rendered second (black card + title are added in post)
EVENTS = dict(impacts=[], shakes=[], whoosh=[], land=[], shatter=[], teleport=[], tremor=(15.6, 19.4),
              boss=(17.6, 23.6), cut=END_T, cuts=[])

# =============================================================== poses (degrees; joint: (rx, ry, rz))
# arms/legs hang down: a NEGATIVE rx swings them forward; torso/head: POSITIVE rx bends forward.
# "R" = the +X limb.
POSES = {
    'idle': dict(z=2.0, torso=(0, 0, 0), head=(0, 0, 0), armL=(0, 7, 0), armR=(0, -7, 0), legL=(0, 0, 0),
                 legR=(0, 0, 0)),
    'idle2': dict(z=2.0, torso=(2, 0, 0), head=(-3, 0, 0), armL=(4, 9, 0), armR=(4, -9, 0), legL=(0, 0, 0),
                  legR=(0, 0, 0)),
    'guard': dict(z=1.85, torso=(8, 0, -18), head=(0, 0, 14), armL=(-80, 0, 22), armR=(-62, 0, -28),
                  legL=(-22, 6, 0), legR=(18, -6, 0)),
    'antic': dict(z=1.45, torso=(32, 0, 15), head=(-20, 0, -10), armL=(-50, 0, 20), armR=(55, 0, 0),
                  legL=(-55, 6, 0), legR=(30, -6, 0)),
    'dash': dict(z=1.6, torso=(38, 0, 10), head=(-25, 0, -5), armL=(-40, 0, 15), armR=(70, 0, 0),
                 legL=(-65, 0, 0), legR=(55, 0, 0)),
    'punchR': dict(z=1.8, torso=(16, 0, 32), head=(-8, 0, -28), armL=(-55, 0, 30), armR=(-95, 0, -6),
                   legL=(-30, 6, 0), legR=(25, -6, 0)),
    'punchL': dict(z=1.8, torso=(16, 0, -32), head=(-8, 0, 28), armL=(-95, 0, 6), armR=(-55, 0, -30),
                   legL=(25, 6, 0), legR=(-30, -6, 0)),
    'kick': dict(z=2.05, torso=(-18, 0, -10), head=(14, 0, 8), armL=(-20, 40, 0), armR=(-70, -25, -10),
                 legL=(8, 0, 0), legR=(-105, 0, 0)),
    'block': dict(z=1.8, torso=(12, 0, 0), head=(12, 0, 0), armL=(-105, 0, 38), armR=(-105, 0, -38),
                  legL=(-20, 8, 0), legR=(20, -8, 0)),
    'hit': dict(z=2.0, torso=(-28, 0, 0), head=(-30, 0, 0), armL=(-125, 25, 0), armR=(-125, -25, 0),
                legL=(-35, 0, 0), legR=(-10, 0, 0)),
    'fly': dict(z=2.6, torso=(-35, 0, 0), head=(-30, 0, 0), armL=(-150, 40, 0), armR=(-150, -40, 0),
                legL=(-60, 10, 0), legR=(-20, -10, 0)),
    'air': dict(z=2.0, torso=(10, 0, 0), head=(-8, 0, 0), armL=(-60, 20, 0), armR=(-175, 0, 0),
                legL=(-75, 0, 0), legR=(-25, 0, 0)),
    'airpunch': dict(z=2.0, torso=(20, 0, 25), head=(-10, 0, -20), armL=(-40, 20, 20), armR=(-92, 0, 0),
                     legL=(-70, 0, 0), legR=(-15, 0, 0)),
    'slam': dict(z=2.0, torso=(55, 0, 0), head=(-30, 0, 0), armL=(-40, 35, 0), armR=(-150, 0, 0),
                 legL=(-50, 0, 0), legR=(10, 0, 0)),
    'land': dict(z=1.25, torso=(28, 0, 0), head=(-18, 0, 0), armL=(-15, 45, 0), armR=(-15, -45, 0),
                 legL=(-70, 8, 0), legR=(-35, -8, 0)),
    'kneel': dict(z=1.05, torso=(25, 0, 0), head=(-10, 0, 0), armL=(-25, 15, 0), armR=(-50, -10, 0),
                  legL=(-88, 0, 0), legR=(5, 0, 0)),
    'lie': dict(z=0.55, torso=(0, 0, 0), head=(-10, 0, 20), armL=(-15, 55, 0), armR=(-10, -40, 0),
                legL=(0, 12, 0), legR=(-15, -8, 0), rx=-90),
    'runA': dict(z=1.9, torso=(18, 0, 6), head=(-14, 0, 0), armL=(-60, 0, 0), armR=(50, 0, 0), legL=(-55, 0, 0),
                 legR=(40, 0, 0)),
    'runB': dict(z=1.9, torso=(18, 0, -6), head=(-14, 0, 0), armL=(50, 0, 0), armR=(-60, 0, 0), legL=(40, 0, 0),
                 legR=(-55, 0, 0)),
    'walkA': dict(z=2.0, torso=(0, 0, 4), head=(0, 0, 0), armL=(-12, 6, 0), armR=(10, -6, 0), legL=(-24, 0, 0),
                  legR=(20, 0, 0)),
    'walkB': dict(z=2.0, torso=(0, 0, -4), head=(0, 0, 0), armL=(10, 6, 0), armR=(-12, -6, 0), legL=(20, 0, 0),
                  legR=(-24, 0, 0)),
    'catch': dict(z=2.0, torso=(-2, 0, 18), head=(4, 0, -12), armL=(0, 6, 0), armR=(-90, 0, -8), legL=(0, 0, 0),
                  legR=(0, 0, 0)),
    'duck': dict(z=1.5, torso=(30, 0, 0), head=(-15, 0, 0), armL=(0, 8, 0), armR=(0, -8, 0), legL=(-40, 4, 0),
                 legR=(-20, -4, 0)),
    'raise': dict(z=2.0, torso=(-6, 0, 0), head=(-12, 0, 0), armL=(0, 8, 0), armR=(-178, 0, 0), legL=(-6, 4, 0),
                  legR=(6, -4, 0)),
}
JOINTS = ('torso', 'head', 'armL', 'armR', 'legL', 'legR')


class Actor:
    def __init__(self, rig):
        self.rig = rig
        self.loc = Vector((0, 0, 0))
        self.rz = 0.0

    def face_angle(self, tgt, loc):
        dx, dy = tgt[0] - loc[0], tgt[1] - loc[1]
        a = math.atan2(dx, -dy)
        while a - self.rz > math.pi:
            a -= 2 * math.pi
        while a - self.rz < -math.pi:
            a += 2 * math.pi
        return a

    def pose(self, t, name, loc=None, face=None, z=None, rx=None, **over):
        p = dict(POSES[name])
        p.update(over)
        if loc is not None:
            self.loc = Vector((loc[0], loc[1], 0))
        zz = p['z'] if z is None else z
        if loc is not None and len(loc) == 3:
            zz = loc[2]
        if face is not None:
            self.rz = self.face_angle(face, self.loc) if isinstance(face, (tuple, list)) else D(face)
        rxx = D(p.get('rx', 0) if rx is None else rx)
        f = F(t)
        joints = {j: tuple(D(v) for v in p[j]) for j in JOINTS}
        self.rig.key(f, loc=(self.loc.x, self.loc.y, zz), rot=(rxx, 0, self.rz), **joints)


def build_cast():
    cast = {}
    for k in ('suit', 'emo', 'mask', 'blue', 'boss'):
        cast[k] = Actor(chars.R6(k, chars.SPECS[k]))
    return cast


# =============================================================== choreography
def choreography(c):
    A, B, C, Dd, E = c['suit'], c['emo'], c['mask'], c['blue'], c['boss']
    imp = EVENTS['impacts']

    def hit(t, pos, size=1.0, color=(1.0, 0.85, 0.6), dust_n=0, deb=0, wave=False, seed=0):
        Wd.impact(t, pos, size, color)
        imp.append((t, size))
        EVENTS['shakes'].append((t, 9 * size))
        if dust_n:
            Wd.dust(t, (pos[0], pos[1], 0), n=dust_n, spread=3 * size, size=1.3 * size, seed=seed)
        if deb:
            Wd.debris(t, pos, n=deb, speed=9 * size, seed=seed)
        if wave:
            Wd.shockwave(t, (pos[0], pos[1], 0.15), r_end=10 * size, dur=0.6)

    # hidden extras
    C.pose(0, 'idle', loc=(60, 60, -30), face=0)
    Dd.pose(0, 'idle', loc=(62, 60, -30), face=0)
    E.pose(0, 'idle', loc=(64, 60, -30), face=0)

    # --- 0-5.6 meeting: idle breathing, close-ups
    for t, nm in ((0.0, 'idle'), (1.4, 'idle2'), (2.8, 'idle'), (4.2, 'idle2'), (5.4, 'idle')):
        A.pose(t, nm, loc=(-4, 0), face=(4, 0))
        B.pose(t, nm, loc=(4, 0), face=(-4, 0))
    A.pose(3.6, 'idle', head=(-4, 0, 9))
    B.pose(4.9, 'idle2', head=(9, 0, 0))

    # --- 5.6-7.4 the dash
    A.pose(5.85, 'antic', loc=(-4, 0), face=(4, 0))
    A.pose(6.1, 'dash', loc=(-0.6, 0))
    A.pose(6.3, 'punchR', loc=(2.0, 0))
    B.pose(6.15, 'block', loc=(4, 0), face=(-4, 0))
    hit(6.33, (3.3, 0, 3.6), 1.4, dust_n=8, deb=10, wave=True, seed=1)
    EVENTS['whoosh'].append(6.0)
    B.pose(6.6, 'block', loc=(6.6, 0), z=1.7)
    Wd.dust(6.4, (5.0, 0, 0), n=6, spread=2.5, size=1.6, seed=2)
    A.pose(6.6, 'guard', loc=(2.2, 0))
    A.pose(7.2, 'guard', loc=(1.8, 0))
    B.pose(7.2, 'guard', loc=(6.2, 0), face=(1.8, 0))

    # --- 7.4-9.6 exchange
    B.pose(7.6, 'antic', loc=(5.8, 0), z=1.7)
    B.pose(7.78, 'punchL', loc=(4.4, 0))
    A.pose(7.65, 'guard', loc=(1.8, 0))
    A.pose(7.8, 'duck', loc=(1.6, 0.9))                       # dodges under
    EVENTS['whoosh'].append(7.7)
    A.pose(8.0, 'guard', loc=(1.8, 0.4))
    A.pose(8.12, 'punchR', loc=(2.6, 0.2), face=(4.4, 0))
    B.pose(8.05, 'block', loc=(4.6, 0), face=(2.6, 0))
    hit(8.15, (3.7, 0.1, 3.8), 0.8, seed=3)
    B.pose(8.35, 'guard', loc=(4.8, 0))
    B.pose(8.52, 'kick', loc=(4.4, 0))
    EVENTS['whoosh'].append(8.42)
    A.pose(8.5, 'guard', loc=(2.4, 0.2))
    hit(8.6, (2.6, 0.1, 2.9), 1.5, dust_n=6, wave=True, seed=4)
    A.pose(8.64, 'hit', loc=(1.4, 0.1))
    A.pose(8.82, 'fly', loc=(-3.0, 0.1, 2.8))
    A.pose(9.0, 'fly', loc=(-8.0, 0.1, 2.6))
    Wd.shatter('P1', 9.0, (-1, 0), power=13, seed=5)
    EVENTS['shatter'].append(9.0)
    hit(9.0, (-9.2, 0, 3.0), 1.2, dust_n=10, deb=12, seed=6)
    A.pose(9.25, 'hit', loc=(-11.0, 0.1, 1.4), rx=-30)
    A.pose(9.45, 'lie', loc=(-11.8, 0.1), face=(4, 0))
    B.pose(8.75, 'guard', loc=(4.3, 0), face=(-11, 0))
    B.pose(9.6, 'guard', loc=(4.3, 0))

    # --- 9.6-11.0 rise + air clash
    A.pose(9.8, 'kneel', loc=(-11.5, 0.1), face=(4, 0), rx=0)
    A.pose(10.0, 'antic', loc=(-11.0, 0.1), z=1.4)
    EVENTS['whoosh'].append(10.05)
    A.pose(10.18, 'air', loc=(-6.0, 0, 6.0))
    A.pose(10.42, 'airpunch', loc=(-1.8, 0, 7.4))
    B.pose(10.0, 'antic', loc=(4.3, 0), z=1.4, face=(-6, 0))
    B.pose(10.18, 'air', loc=(3.0, 0, 6.0))
    B.pose(10.42, 'airpunch', loc=(1.8, 0, 7.4), face=(-1.8, 0))
    hit(10.45, (0, 0, 8.6), 2.2, color=(0.75, 0.85, 1.0), seed=7)
    Wd.shockwave(10.45, (0, 0, 8.6), r_end=16, dur=0.7, flat=False)
    A.pose(10.72, 'fly', loc=(-4.5, 0, 5.0))
    B.pose(10.72, 'fly', loc=(4.5, 0, 5.0))
    A.pose(10.95, 'land', loc=(-6.5, 0), rx=0)
    B.pose(10.95, 'land', loc=(6.5, 0))
    for p in ((-6.5, 0), (6.5, 0)):
        Wd.dust(10.95, (p[0], p[1], 0), n=7, spread=3, size=1.8, seed=int(p[0]))
    EVENTS['land'] += [10.95]

    # --- 11.0-12.8 reinforcements drop in
    A.pose(11.3, 'guard', loc=(-6.5, 0), face=(6.5, 0))
    B.pose(11.3, 'guard', loc=(6.5, 0), face=(-6.5, 0))
    C.pose(11.0, 'air', loc=(13, -7, 15), face=(-6.5, 0))
    C.pose(11.45, 'land', loc=(8.0, -3.4))
    Dd.pose(11.15, 'air', loc=(13, 7, 15), face=(-6.5, 0))
    Dd.pose(11.65, 'land', loc=(8.0, 3.4))
    for t, p in ((11.45, (8, -3.4)), (11.65, (8, 3.4))):
        Wd.dust(t, (p[0], p[1], 0), n=7, spread=3, size=2.0, seed=int(t * 10))
        Wd.shockwave(t, (p[0], p[1], 0.1), r_end=7, dur=0.5)
        EVENTS['land'].append(t)
        EVENTS['shakes'].append((t, 6))
    B.pose(11.6, 'guard', head=(0, 0, 60))
    B.pose(12.0, 'guard', head=(0, 0, 14))
    C.pose(11.9, 'guard', loc=(7.8, -3.4), face=(-6.5, 0))
    Dd.pose(12.1, 'guard', loc=(7.8, 3.4), face=(-6.5, 0))
    A.pose(12.6, 'guard', loc=(-6.5, 0), face=(6.5, 0), head=(0, 0, 4))

    # --- 12.8-15.6 team attack
    C.pose(12.9, 'antic', loc=(7.6, -3.4))
    C.pose(13.08, 'dash', loc=(0, -1.6))
    C.pose(13.24, 'punchR', loc=(-3.9, -0.7), face=(-6.5, 0))
    EVENTS['whoosh'].append(12.98)
    A.pose(13.15, 'block', loc=(-6.4, 0), face=(-3.9, -0.7))
    hit(13.28, (-4.9, -0.4, 3.6), 1.0, seed=8)
    Dd.pose(12.9, 'runA', loc=(7.4, 3.6), face=(0, 5.5))
    Dd.pose(13.08, 'runB', loc=(2.5, 5.5), face=(-4, 5))
    Dd.pose(13.26, 'runA', loc=(-2.5, 5.4), face=(-6.4, 0))
    Dd.pose(13.42, 'antic', loc=(-4.8, 3.6))
    Dd.pose(13.58, 'kick', loc=(-5.6, 2.6), face=(-6.4, 0))
    EVENTS['whoosh'].append(13.48)
    hit(13.63, (-6.2, 1.0, 3.0), 1.3, dust_n=5, seed=9)
    A.pose(13.66, 'hit', loc=(-6.7, -0.9), face=(-5.6, 2.6))
    A.pose(13.85, 'hit', loc=(-7.0, -1.6), z=1.8)
    C.pose(13.6, 'guard', loc=(-3.7, -1.2))
    B.pose(13.25, 'antic', loc=(6.4, 0), z=1.4, face=(-6.6, -1.6))
    B.pose(13.48, 'air', loc=(1.5, -0.6, 9.5))
    B.pose(13.8, 'air', loc=(-4.6, -1.3, 11.5))
    B.pose(14.08, 'slam', loc=(-6.8, -1.6, 6.8))
    EVENTS['whoosh'].append(13.95)
    hit(14.13, (-7.0, -1.6, 2.2), 2.2, dust_n=12, deb=18, wave=True, seed=10)
    Wd.cracks(14.13, (-7.0, -1.6), n=8, length=7, color=(1.0, 0.55, 0.2), seed=11, dur=0.3, width=0.14)
    A.pose(14.2, 'lie', loc=(-7.0, -1.6), face=(4, 0))
    B.pose(14.4, 'land', loc=(-4.8, -1.0), face=(-7, -1.6))
    B.pose(14.9, 'guard', loc=(-4.6, -0.8))
    C.pose(14.6, 'guard', loc=(-3.6, -2.4), face=(-7, -1.6))
    Dd.pose(14.6, 'guard', loc=(-5.2, 2.8), face=(-7, -1.6))
    A.pose(15.4, 'lie', loc=(-7.0, -1.6))

    # --- 15.6-19.4 the strongest arrives
    boss_xy = (0.0, 14.0)
    A.pose(15.9, 'kneel', loc=(-7.0, -1.6), rx=0, face=(0, 14))
    A.pose(16.5, 'guard', loc=(-6.8, -1.6), face=(0, 12))
    for act, p in ((B, (-4.6, -0.8)), (C, (-3.6, -2.4)), (Dd, (-5.2, 2.8))):
        act.pose(16.0, 'guard', loc=p, head=(0, 0, 40))
        act.pose(16.5, 'guard', loc=p, face=(0, 12))
        act.pose(18.9, 'guard', loc=p, face=(0, 9))
    A.pose(18.9, 'guard', loc=(-6.8, -1.6), face=(0, 9))
    Wd.smoke_cloud(15.8, 23.0, (0, 18), n=20, radius=6, color=(0.03, 0.03, 0.035), seed=12, rise=2.5)
    E.pose(16.35, 'idle', loc=(64, 60, -30), face=0)
    E.pose(16.4, 'walkA', loc=boss_xy, face=(0, 0))
    steps = [(16.4 + i * 0.6, 'walkB' if i % 2 else 'walkA', 14.0 - 0.9 * i) for i in range(1, 6)]
    for t, nm, y in steps:
        E.pose(t, nm, loc=(0, y), face=(0, 0))
        EVENTS['land'].append(t)
    E.pose(19.4, 'idle', loc=(0, 9.0), face=(-5, 0))
    Wd.cracks(17.6, (0, 10.6), n=11, length=16, seed=13, dur=1.0)
    Wd.aura(16.4, END_T, E.rig.root, n=36, seed=14)

    # --- 19.4-23.0 everyone attacks; the boss is on another level
    bz = (0, 9.0)
    for act, start, end, s in ((A, (-6.8, -1.6), (-1.9, 6.9), 0), (B, (-4.6, -0.8), (1.9, 6.9), 1),
                               (C, (-3.6, -2.4), (-2.7, 9.2), 2), (Dd, (-5.2, 2.8), (2.8, 9.4), 3)):
        for k in range(4):
            f = k / 3
            p = (start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f)
            act.pose(19.45 + k * 0.2, 'runA' if (k + s) % 2 else 'runB', loc=p, face=bz)
    A.pose(20.1, 'punchR', loc=(-1.6, 7.2), face=bz)
    E.pose(20.0, 'idle', loc=bz, face=(-1.6, 7.2))
    E.pose(20.12, 'catch', loc=bz)
    hit(20.15, (-0.7, 8.0, 3.8), 1.2, color=(1.0, 0.3, 0.2), seed=15)
    A.pose(20.35, 'hit', loc=(-3.4, 6.2), face=bz)
    A.pose(20.6, 'guard', loc=(-3.8, 5.8))
    C.pose(20.15, 'punchR', loc=(-1.9, 9.1), face=bz)
    Dd.pose(20.18, 'punchL', loc=(2.0, 9.3), face=bz)
    E.pose(20.25, 'duck', loc=bz, face=(0, 0))                 # both punches pass over his head
    EVENTS['whoosh'] += [20.18, 20.22]
    C.pose(20.4, 'dash', loc=(-0.6, 9.0))
    Dd.pose(20.4, 'dash', loc=(0.8, 9.1))
    B.pose(20.25, 'antic', loc=(1.9, 6.9), z=1.4, face=bz)
    B.pose(20.5, 'air', loc=(1.0, 7.6, 6.5))
    # teleport behind B
    E.pose(20.55, 'idle', loc=bz)
    E.pose(20.58, 'idle', loc=(3.6, 5.2), face=(1.0, 7.6))
    EVENTS['teleport'] += [20.56]
    Wd.impact(20.56, (0, 9, 3), 1.0, (1.0, 0.1, 0.05))
    Wd.impact(20.6, (3.6, 5.2, 3), 1.0, (1.0, 0.1, 0.05))
    E.pose(20.72, 'punchR', loc=(3.0, 5.8), face=(1.0, 7.6))
    hit(20.76, (1.6, 7.0, 5.0), 1.8, color=(1.0, 0.25, 0.15), seed=16)
    B.pose(20.78, 'fly', loc=(0.4, 8.6, 6.0), face=(3.0, 5.8))
    B.pose(21.15, 'fly', loc=(-9.0, 15.5, 3.0))
    B.pose(21.35, 'lie', loc=(-11.5, 17.5), face=(3, 5.8))
    Wd.dust(21.35, (-11.5, 17.5, 0), n=6, seed=17)
    # D next: teleport, kick
    Dd.pose(20.9, 'guard', loc=(1.4, 9.4), face=(3.0, 5.8))
    E.pose(20.98, 'idle', loc=(3.0, 5.8))
    E.pose(21.01, 'idle', loc=(3.9, 9.6), face=(1.4, 9.4))
    EVENTS['teleport'] += [21.0]
    Wd.impact(21.0, (3.9, 9.6, 3), 0.9, (1.0, 0.1, 0.05))
    E.pose(21.15, 'kick', loc=(3.4, 9.5), face=(1.4, 9.4))
    hit(21.2, (1.9, 9.4, 3.2), 1.7, color=(1.0, 0.25, 0.15), seed=18)
    Dd.pose(21.22, 'fly', loc=(0.5, 9.4, 3.0), face=(3.4, 9.5))
    Dd.pose(21.55, 'fly', loc=(-9.0, 9.0, 2.6))
    Dd.pose(21.75, 'lie', loc=(-13.0, 8.6))
    Wd.dust(21.75, (-13, 8.6, 0), n=6, seed=19)
    # C: catches the punch and throws him
    C.pose(21.2, 'guard', loc=(-0.4, 9.0), face=(3.4, 9.5))
    C.pose(21.38, 'punchR', loc=(1.2, 9.3))
    E.pose(21.4, 'catch', loc=(3.4, 9.5), face=(1.2, 9.3))
    hit(21.42, (2.3, 9.4, 3.8), 1.0, color=(1.0, 0.25, 0.15), seed=20)
    E.pose(21.55, 'punchL', loc=(3.0, 9.4))
    hit(21.58, (1.6, 9.3, 3.6), 1.7, color=(1.0, 0.25, 0.15), seed=21)
    C.pose(21.6, 'fly', loc=(-0.5, 9.2, 3.2), face=(3.0, 9.4))
    C.pose(21.95, 'fly', loc=(-9.5, 12.0, 2.5))
    C.pose(22.15, 'lie', loc=(-13.5, 13.0))
    # A: the last one
    A.pose(21.6, 'antic', loc=(-3.8, 5.8), z=1.4, face=(3.0, 9.4))
    A.pose(21.8, 'dash', loc=(-0.6, 7.6))
    A.pose(21.95, 'punchR', loc=(1.2, 8.6))
    EVENTS['whoosh'].append(21.85)
    E.pose(21.85, 'idle', loc=(3.0, 9.4), face=(1.2, 8.6))
    E.pose(21.95, 'catch', loc=(3.0, 9.4))
    hit(21.98, (2.1, 9.0, 3.8), 1.0, color=(1.0, 0.25, 0.15), seed=22)
    E.pose(22.18, 'punchR', loc=(2.7, 9.3))
    hit(22.22, (1.6, 8.7, 3.8), 2.4, color=(1.0, 0.2, 0.1), dust_n=8, wave=True, seed=23)
    A.pose(22.25, 'fly', loc=(0.6, 8.1, 3.2), face=(2.7, 9.3))
    A.pose(22.6, 'fly', loc=(-6.0, 1.5, 3.0))
    A.pose(22.85, 'lie', loc=(-9.5, -2.0))
    Wd.dust(22.85, (-9.5, -2.0, 0), n=8, seed=24)

    # --- 23.0-25.4 the final wave
    E.pose(23.0, 'idle', loc=(2.7, 9.3), face=(2.7, 0))
    E.pose(23.5, 'raise', loc=(2.7, 9.3))
    Wd.energy_sphere(23.75, 25.2, (2.7, 9.3, 7.5), r_end=55)
    Wd.shockwave(23.75, (2.7, 9.3, 0.2), r_end=40, dur=1.2, color=(1.0, 0.15, 0.05), strength=14)
    Wd.cracks(23.75, (2.7, 9.3), n=14, length=26, seed=25, dur=0.8, width=0.3)
    EVENTS['impacts'].append((23.75, 3.0))
    EVENTS['shakes'].append((23.75, 26))
    for act in (A, B, C, Dd):
        p = (act.loc.x, act.loc.y)
        act.pose(23.9, 'lie', loc=p)
        act.pose(24.0, 'lie', loc=(p[0] - 0.8, p[1] - 0.4), z=0.9)
        act.pose(24.2, 'lie', loc=(p[0] - 1.2, p[1] - 0.6))
    E.pose(25.3, 'idle', loc=(2.7, 9.3), face=(2.7, 0))
    E.pose(END_T, 'idle2', loc=(2.7, 9.3))


# =============================================================== cameras
CAM = None
TGT = None


def shot(t0, t1, p0, p1, l0, l1, lens=35, fstop=2.8):
    f0, f1 = F(t0), F(t1) - 1
    EVENTS['cuts'].append(t0)
    for f, p, l in ((f0, p0, l0), (f1, p1, l1)):
        CAM.location = p
        CAM.keyframe_insert('location', frame=f)
        TGT.location = l
        TGT.keyframe_insert('location', frame=f)
        CAM.data.lens = lens
        CAM.data.keyframe_insert('lens', frame=f)
        CAM.data.dof.aperture_fstop = fstop
        CAM.data.dof.keyframe_insert('aperture_fstop', frame=f)


def cameras():
    global CAM, TGT
    sc = bpy.context.scene
    bpy.ops.object.camera_add()
    CAM = bpy.context.object
    sc.camera = CAM
    TGT = bpy.data.objects.new('cam_tgt', None)
    bpy.context.collection.objects.link(TGT)
    con = CAM.constraints.new('TRACK_TO')
    con.target = TGT
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    CAM.data.dof.use_dof = True
    CAM.data.dof.focus_object = TGT
    CAM.data.sensor_fit = 'VERTICAL'
    CAM.data.sensor_height = 24
    CAM.data.clip_end = 400
    # 1 meeting
    shot(0.0, 3.0, (-16, -26, 8), (-6.5, -13, 3.0), (0, 0, 6), (0, 0, 3.4), 30, 4.0)
    shot(3.0, 4.3, (0.6, -2.4, 4.3), (0.2, -2.0, 4.4), (-4, 0, 4.7), (-4, 0, 4.7), 40, 1.8)
    shot(4.3, 5.6, (-0.4, -2.2, 3.4), (-0.1, -1.9, 3.6), (4, 0, 4.8), (4, 0, 4.7), 40, 1.8)
    # 2 battle
    shot(5.6, 7.4, (-3, -14, 3.0), (3, -13, 3.2), (-1, 0, 3.2), (4, 0, 3.0), 30, 3.2)
    shot(7.4, 8.55, (8.5, -7, 2.4), (6.5, -9, 3.2), (3, 0, 3.4), (3, 0, 3.4), 30, 3.2)
    shot(8.55, 9.6, (-1, -11, 2.2), (-7, -11, 2.6), (1, 0, 3), (-9, 0, 2.6), 26, 4.0)
    shot(9.6, 11.0, (2, -16, 1.2), (-2, -17, 2.0), (-3, 0, 5), (0, 0, 6.5), 24, 5.0)
    # 3 reinforcements + team attack
    shot(11.0, 12.8, (14, -1, 1.0), (13, 0, 1.4), (6, 0, 4.5), (6, 0, 3.4), 24, 4.0)
    shot(12.8, 14.6, (2, -14, 2.4), (-2, -14, 5.0), (-4, 0, 4), (-6, -1, 2.4), 26, 5.0)
    shot(14.6, 15.6, (-10, -6, 1.0), (-9.5, -6.5, 1.3), (-7, -1.6, 0.8), (-7, -1.6, 0.8), 40, 2.0)
    # 4 the strongest
    shot(15.6, 17.0, (-4, -12, 3.6), (-3, -9, 4.0), (0, 14, 4.5), (0, 14, 5.0), 30, 6.0)
    shot(17.0, 18.4, (2.6, 5.5, 0.6), (2.2, 6.0, 0.8), (0, 11.5, 4.4), (0, 10.8, 4.6), 26, 2.2)
    shot(18.4, 19.4, (0.5, 5.2, 4.5), (0.4, 5.6, 4.6), (0, 9.8, 4.7), (0, 9.2, 4.7), 50, 1.6)
    # 5 everyone vs the boss
    shot(19.4, 20.5, (-9, -2, 3.0), (-6, -1, 3.8), (-2, 6, 3.4), (0, 8.5, 3.4), 26, 4.0)
    shot(20.5, 21.3, (6.5, 1.0, 2.2), (6.0, 2.0, 3.0), (2.5, 6.5, 4.4), (-4, 12, 3.4), 30, 4.0)
    shot(21.3, 22.1, (5.0, 15.5, 2.0), (4.4, 15.0, 2.6), (2.0, 9.4, 3.4), (1.0, 9.3, 3.4), 32, 3.5)
    shot(22.1, 23.0, (6.5, 12.5, 3.0), (6.8, 13.0, 3.6), (1.5, 8.8, 3.6), (-7, 0, 2.4), 26, 6.0)
    # 6 finale
    shot(23.0, 25.4, (9, -6, 1.0), (10, -8, 1.4), (2.7, 9.3, 4.6), (2.7, 9.3, 5.4), 24, 6.0)
    shot(25.4, END_T + 0.05, (2.7, 1.0, 4.6), (2.7, 5.4, 4.62), (2.7, 9.3, 4.62), (2.7, 9.3, 4.62), 45, 1.8)


# =============================================================== lighting
def lighting():
    sc = bpy.context.scene
    w = bpy.data.worlds.new('night')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (0.03, 0.04, 0.07, 1)
    bg.inputs[1].default_value = 1.0
    bpy.ops.object.light_add(type='SUN', rotation=(D(62), 0, D(200)))
    moon = bpy.context.object
    moon.data.energy = 3.5
    moon.data.color = (0.55, 0.68, 1.0)
    moon.data.angle = D(2)
    bpy.ops.object.light_add(type='AREA', location=(0, -6, 16))
    fill = bpy.context.object
    fill.data.energy = 3000
    fill.data.size = 20
    fill.data.color = (0.5, 0.6, 0.9)
    # cold backlight: rim-lights the characters against the haze (the look of the reference clips)
    bpy.ops.object.light_add(type='SPOT', location=(0, 24, 14))
    rim = bpy.context.object
    rim.data.energy = 60000
    rim.data.color = (0.6, 0.75, 1.0)
    rim.data.spot_size = D(70)
    rim.data.spot_blend = 0.8
    rim.data.shadow_soft_size = 2
    con = rim.constraints.new('TRACK_TO')
    tgt = bpy.data.objects.new('rim_tgt', None)
    bpy.context.collection.objects.link(tgt)
    con.target = tgt
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    bpy.ops.object.light_add(type='SPOT', location=(-20, -6, 10))
    rim2 = bpy.context.object
    rim2.data.energy = 30000
    rim2.data.color = (1.0, 0.6, 0.35)
    rim2.data.spot_size = D(60)
    rim2.data.spot_blend = 0.8
    c2 = rim2.constraints.new('TRACK_TO')
    c2.target = tgt
    c2.track_axis = 'TRACK_NEGATIVE_Z'
    c2.up_axis = 'UP_Y'
    for t, e in ((15.6, 60000), (16.5, 15000)):
        rim.data.energy = e
        rim.data.keyframe_insert('energy', frame=F(t))
    # boss red light (keyed)
    bpy.ops.object.light_add(type='POINT', location=(0, 13, 6))
    red = bpy.context.object
    red.data.color = (1.0, 0.08, 0.04)
    red.data.shadow_soft_size = 3
    for t, e in ((15.6, 0), (16.4, 0), (17.2, 7000), (END_T, 7000)):
        red.data.energy = e
        red.data.keyframe_insert('energy', frame=F(t))
    red.location = (0, 13, 6)
    red.keyframe_insert('location', frame=F(16.0))
    red.location = (2.7, 13.5, 7)
    red.keyframe_insert('location', frame=F(23.0))
    # lamps flicker and die when he arrives
    for i, L in enumerate(Wd.LAMPS):
        for t, e in ((15.6, 6000), (15.8, 800), (15.9, 6000), (16.1, 400), (16.2, 4000), (16.4, 0)):
            L.data.energy = e
            L.data.keyframe_insert('energy', frame=F(t + i * 0.03))
    for t, e in ((15.6, 3.5), (16.5, 1.2)):
        moon.data.energy = e
        moon.data.keyframe_insert('energy', frame=F(t))
    for t, e in ((15.6, 3000), (16.5, 600)):
        fill.data.energy = e
        fill.data.keyframe_insert('energy', frame=F(t))
    Wd.key_fog(15.6, (0.045, 0.06, 0.09), 0.016)
    Wd.key_fog(16.8, (0.10, 0.02, 0.02), 0.02)


def render_settings(res=(540, 960)):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 12
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.cycles.diffuse_bounces = 1
    sc.cycles.glossy_bounces = 1
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.45
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
    sc.view_settings.exposure = 0.8
    sc.frame_start, sc.frame_end = 1, F(END_T)


def build():
    Wd.ground()
    Wd.buildings()
    Wd.debris_field()
    Wd.lamps()
    Wd.pillar('P1', (-10.2, 0.4), size=(2.4, 2.4, 10), grid=(2, 2, 6))
    Wd.pillar('P2', (11, 9), size=(2.4, 2.4, 9), grid=(2, 2, 5))
    Wd.pillar('P3', (-12, 12), size=(2.4, 2.4, 11), grid=(2, 2, 6))
    cast = build_cast()
    choreography(cast)
    cameras()
    lighting()
    Wd.apply_fog()
    render_settings()
    json.dump(EVENTS, open(os.path.join(HERE, 'events.json'), 'w'), indent=1)
    return cast


if __name__ == '__main__':
    build()
    sc = bpy.context.scene
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    mode = args[0] if args else 'still'
    out = os.path.join(HERE, 'frames')
    os.makedirs(out, exist_ok=True)
    if mode == 'render':
        a, b = int(args[1]), int(args[2])
        sc.frame_start, sc.frame_end = a, b
        sc.render.filepath = os.path.join(out, '')
        bpy.ops.render.render(animation=True)
    else:
        import time
        for fr in args[1:]:
            sc.frame_set(int(fr))
            sc.render.filepath = os.path.join(HERE, 'stills', 'f%04d.png' % int(fr))
            t = time.time()
            bpy.ops.render.render(write_still=True)
            print('STILL', fr, round(time.time() - t, 1), flush=True)
