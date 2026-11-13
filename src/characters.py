"""Characters: the hero (and other people), the monsters, the dog, props."""
import math
import cairo
from engine import *

R = math.radians

# ---------------------------------------------------------------- people
HERO_STYLE = dict(
    skin=hexc('#c98d5f'), skin_d=hexc('#9c6640'), shirt=hexc('#243461'), shirt_d=hexc('#18234a'),
    pants=hexc('#141a30'), shoe=hexc('#0b0d16'), hair=None, eye=hexc('#f1ede2'), pupil=hexc('#121212'),
    mouth=hexc('#4a1d14'), brow=hexc('#2a1a12'))

MAN_STYLE = dict(
    skin=hexc('#e1b38c'), skin_d=hexc('#b5835d'), shirt=hexc('#6b5a45'), shirt_d=hexc('#4f412f'),
    pants=hexc('#2c2f36'), shoe=hexc('#121212'), hair=hexc('#2b1d14'), eye=hexc('#f1ede2'),
    pupil=hexc('#121212'), mouth=hexc('#4a1d14'), brow=hexc('#2b1d14'))

CROWD_STYLES = [
    dict(MAN_STYLE, shirt=hexc('#7a2f2f'), shirt_d=hexc('#5a2222'), hair=hexc('#1c1410')),
    dict(MAN_STYLE, shirt=hexc('#3e5f4a'), shirt_d=hexc('#2c4535'), skin=hexc('#a8714a'), skin_d=hexc('#7f5232')),
    dict(MAN_STYLE, shirt=hexc('#8a7a3a'), shirt_d=hexc('#665a2a'), hair=hexc('#6a4a2a')),
    dict(MAN_STYLE, shirt=hexc('#4a4f7a'), shirt_d=hexc('#363a5c'), hair=None),
]

THIGH, SHIN = 92, 92
HIP_H = 192
TORSO = 150
HEAD_R = 52
UARM, FARM = 80, 78


class Pose(dict):
    """Pose with defaults. Angles in degrees."""
    DEF = dict(facing=1, lean=0.0, hip_dy=0.0, hip_dx=0.0,
               legs=(0, 0, 0, 0), foot=(0, 0),
               hand_b=None, hand_f=None, bend_b=-1, bend_f=-1,
               head_tilt=0.0, head_dy=0.0,
               eyes='open', look=(0.0, 0.0), brows='neutral', mouth='smile', blink=True,
               backpack=False, flashlight=None, sweat=0.0, tremble=0.0,
               lit=1.0, rim=None, sil=None, t=0.0, style=None, lying=False, hide_legs=False,
               hand_mouth=False, mouth_open=0.0)

    def __getattr__(self, k):
        if k in self:
            return self[k]
        return Pose.DEF[k]

    def __setattr__(self, k, v):
        self[k] = v


def walk_pose(p, amp=1.0):
    a = math.sin(p * 2 * math.pi)
    b = math.cos(p * 2 * math.pi)
    tf, tb = 26 * a * amp, -26 * a * amp
    kf = max(0, -b) * 38 * amp + 4
    kb = max(0, b) * 38 * amp + 4
    bob = -abs(b) * 5 * amp
    hf = (14 - 34 * a * amp, 148)
    hb = (14 + 34 * a * amp, 148)
    return dict(legs=(tb, kb, tf, kf), hip_dy=bob, hand_f=hf, hand_b=hb, lean=3 * amp)


def run_pose(p):
    a = math.sin(p * 2 * math.pi)
    b = math.cos(p * 2 * math.pi)
    tf, tb = 42 * a, -42 * a
    kf = max(0, -b) * 85 + 10
    kb = max(0, b) * 85 + 10
    bob = -abs(b) * 14 + 6
    hf = (20 - 55 * a, 95 - 20 * abs(a))
    hb = (20 + 55 * a, 95 - 20 * abs(a))
    return dict(legs=(tb, kb, tf, kf), hip_dy=bob, hand_f=hf, hand_b=hb, lean=14, bend_f=1, bend_b=1)


def sneak_pose(p):
    a = math.sin(p * 2 * math.pi)
    b = math.cos(p * 2 * math.pi)
    tf, tb = 30 * a, -30 * a
    kf = max(0, -b) * 70 + 12
    kb = max(0, b) * 70 + 12
    bob = -abs(b) * 12 - 10
    return dict(legs=(tb, kb, tf, kf), hip_dy=bob, foot=(-25, -25), lean=10,
                hand_f=(48, 60 + 8 * a), hand_b=(30, 66 - 8 * a), bend_f=1, bend_b=1)


def crouch_pose():
    # sitting on the floor hugging knees (side view)
    return dict(legs=(118, 140, 128, 150), hip_dy=170, lean=-8, hand_f=(70, 92), hand_b=(64, 88),
                bend_f=-1, bend_b=-1, foot=(0, 0))


class Person:
    def __init__(self, style=None):
        self.st = style or HERO_STYLE

    def col(self, name, k=1.0, P=None):
        if P.sil is not None:
            return P.sil
        c = self.st[name]
        return mul(c, k * P.lit)

    # ---------------------------------------------------------------- draw
    def draw(self, ctx, x, y, s, P):
        """Draw at feet position (x, y) with scale s. Returns key world points."""
        P = Pose(P)
        if P.style is not None:
            self.st = P.style
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(s, s)
        out = {}
        if P.facing == 0:
            out = self._front(ctx, P)
        else:
            if P.facing < 0:
                ctx.scale(-1, 1)
            if P.rim is not None and P.sil is not None:
                # rim pass: draw silhouette slightly offset in rim colour
                rp = Pose(P)
                rp.sil = P.rim
                rp.rim = None
                ctx.save()
                ctx.translate(3.5 * (1 if P.facing > 0 else -1), -2)
                self._side(ctx, rp)
                ctx.restore()
            out = self._side(ctx, P)
        ctx.restore()
        # convert local points to world
        f = -1 if P.facing < 0 else 1
        res = {}
        for k, v in out.items():
            if isinstance(v, tuple):
                res[k] = (x + v[0] * s * f, y + v[1] * s)
            else:
                res[k] = v if f > 0 else 180 - v
        return res

    # .............................................................. side view
    def _leg(self, ctx, hip, th, kn, foot_ang, k, P):
        a = R(th)
        knee = (hip[0] + THIGH * math.sin(a), hip[1] + THIGH * math.cos(a))
        b = a - R(kn)
        ankle = (knee[0] + SHIN * math.sin(b), knee[1] + SHIN * math.cos(b))
        pc = self.col('pants', k, P)
        taper(ctx, hip, knee, 24, 21, pc)
        taper(ctx, knee, ankle, 21, 17, pc)
        # shoe
        fa = R(foot_ang) + (b if P.lying else 0) * 0
        ctx.save()
        ctx.translate(*ankle)
        ctx.rotate(-fa)
        rrect(ctx, -10, -6, 40, 15, 7, self.col('shoe', k, P))
        ctx.restore()
        return ankle

    def _arm(self, ctx, sh, hand, bend, k, P, tremble=(0, 0)):
        if hand is None:
            hand = (6, 150)
        tgt = (sh[0] + hand[0] + tremble[0], sh[1] + hand[1] + tremble[1])
        tgt = clamp_reach(sh, tgt, UARM + FARM - 1)
        el = ik2(sh, tgt, UARM, FARM, bend)
        c = self.col('shirt', k, P)
        taper(ctx, sh, el, 18, 16, c)
        taper(ctx, el, tgt, 16, 15, c)
        circle(ctx, tgt[0], tgt[1], 10.5, self.col('skin', k, P))
        return el, tgt

    def _side(self, ctx, P):
        t = P.t
        tr = P.tremble
        tx = noise(t * 40, 11) * 2.5 * tr
        ty = noise(t * 37, 12) * 2.5 * tr
        hip = (P.hip_dx, -HIP_H + P.hip_dy)
        lean = R(P.lean)
        sh = (hip[0] + TORSO * math.sin(lean), hip[1] - TORSO * math.cos(lean))
        ux, uy = math.sin(lean), -math.cos(lean)    # up vector of torso
        vx, vy = -uy, ux                              # forward vector

        def T(v, u):
            return (hip[0] + vx * v + ux * u, hip[1] + vy * v + uy * u)

        sh_b = T(-4, 136)
        sh_f = T(10, 134)
        out = {}
        # back arm
        if not P.lying:
            self._arm(ctx, sh_b, P.hand_b, P.bend_b, 0.72, P, (tx, ty))
        # backpack (behind torso)
        if P.backpack:
            bp = [T(-30, 18), T(-62, 30), T(-66, 120), T(-46, 142), T(-24, 140)]
            fill_poly(ctx, bp, self._bp(0.95, P))
            fill_poly(ctx, [T(-48, 60), T(-66, 64), T(-64, 100), T(-46, 100)], self._bp(0.7, P))
        # back leg
        if not P.hide_legs:
            self._leg(ctx, T(-6, 4), P.legs[0], P.legs[1], P.foot[0], 0.72, P)
        # torso (angular)
        tor = [T(-34, -6), T(34, -6), T(40, 104), T(33, 150), T(-27, 154), T(-38, 106)]
        fill_poly(ctx, tor, self.col('shirt', 1, P))
        if P.sil is None:
            ctx.save()
            poly(ctx, tor)
            ctx.clip()
            fill_poly(ctx, [T(-50, -10), T(-14, -10), T(-20, 160), T(-50, 160)], self.col('shirt_d', 1, P))
            ctx.restore()
            # belt line / hem
            line(ctx, T(-34, 4), T(34, 4), 5, self.col('pants', 1.2, P), cairo.LINE_CAP_BUTT)
        if P.backpack:
            line(ctx, T(-22, 146), T(22, 92), 9, self._bp(0.8, P))
            line(ctx, T(22, 92), T(20, 60), 9, self._bp(0.8, P))
        # front leg
        if not P.hide_legs:
            self._leg(ctx, T(6, 4), P.legs[2], P.legs[3], P.foot[1], 1.0, P)
        # neck + head
        hl = lean + R(P.head_tilt) * 0.4
        nb = T(6, 148)
        hc = (nb[0] + math.sin(hl) * 50 + tx * 0.6, nb[1] - math.cos(hl) * 50 + P.head_dy + ty * 0.6)
        line(ctx, nb, (nb[0] + math.sin(hl) * 18, nb[1] - math.cos(hl) * 18), 20, self.col('skin_d', 1, P),
             cairo.LINE_CAP_BUTT)
        self._head_side(ctx, hc, P)
        out['head'] = hc
        # front arm
        el, hand = self._arm(ctx, sh_f, P.hand_f if not P.hand_mouth else
                             (hc[0] - sh_f[0] + 40, hc[1] - sh_f[1] + 30), P.bend_f, 1.0, P, (tx, ty))
        out['hand'] = hand
        out['hip'] = hip
        if P.flashlight is not None:
            ang = R(P.flashlight)
            ctx.save()
            ctx.translate(*hand)
            ctx.rotate(ang)
            rrect(ctx, -10, -7, 40, 14, 3, self.col('shoe', 2.2, P) if P.sil is None else P.sil)
            rect(ctx, 26, -9, 8, 18, hexc('#d8d4c0') if P.sil is None else P.sil)
            ctx.restore()
            circle(ctx, hand[0], hand[1], 10.5, self.col('skin', 1, P))
            out['lens'] = (hand[0] + math.cos(ang) * 34, hand[1] + math.sin(ang) * 34)
            out['lens_ang'] = P.flashlight
        return out

    def _bp(self, k, P):
        if P.sil is not None:
            return P.sil
        return mul(hexc('#3e4c36'), k * P.lit)

    def _head_side(self, ctx, hc, P):
        r = HEAD_R
        x, y = hc
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(R(P.head_tilt))
        # ear (back)
        ellipse(ctx, -0.82 * r, 0.1 * r, 0.2 * r, 0.27 * r, self.col('skin_d', 1, P))
        circle(ctx, 0, 0, r, self.col('skin_d', 1, P))
        if P.sil is not None:
            # nose bump keeps the silhouette readable
            circle(ctx, 0.96 * r, 0.12 * r, 0.14 * r, P.sil)
            ctx.restore()
            return
        ctx.save()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.clip()
        circle(ctx, 0.2 * r, -0.14 * r, 0.96 * r, self.col('skin', 1, P))
        if self.st.get('hair') is not None:
            hp = [(-1.2 * r, -0.2 * r), (-1.1 * r, -1.2 * r), (1.2 * r, -1.2 * r), (0.9 * r, -0.62 * r),
                  (0.55 * r, -0.5 * r), (0.35 * r, -0.62 * r), (0.0, -0.45 * r), (-0.55 * r, -0.4 * r)]
            fill_poly(ctx, hp, self.col('hair', 1, P))
        ctx.restore()
        ellipse(ctx, -0.82 * r, 0.1 * r, 0.12 * r, 0.17 * r, self.col('skin_d', 0.8, P))
        # nose
        circle(ctx, 0.96 * r, 0.12 * r, 0.13 * r, self.col('skin', 0.97, P))
        self._face(ctx, P, [(0.34 * r, -0.08 * r, 1.0), (0.74 * r, -0.08 * r, 0.72)], (0.58 * r, 0.46 * r))
        if P.rim is not None:
            ctx.save()
            ctx.arc(0, 0, r, 0, 2 * math.pi)
            ctx.clip()
            ctx.new_path()
            ctx.arc(0, 0, r, 0, 2 * math.pi)
            ctx.arc_negative(-0.12 * r, 0.04 * r, r, 2 * math.pi, 0)
            src(ctx, P.rim)
            ctx.fill()
            ctx.restore()
        ctx.restore()

    # .............................................................. face
    def _face(self, ctx, P, eyes, mpos):
        r = HEAD_R
        t = P.t
        lx, ly = P.look
        e = P.eyes
        if P.blink and e in ('open', 'wide'):
            ph = (t + 0.37) % 3.3
            if ph < 0.12:
                e = 'closed'
        for (ex, ey, sx) in eyes:
            if e == 'closed':
                ctx.save()
                ctx.translate(ex, ey + 2)
                ctx.scale(sx, 1)
                ctx.arc(0, 0, 0.13 * r, 0.15 * math.pi, 0.85 * math.pi)
                ctx.restore()
                ctx.set_line_width(3.2)
                src(ctx, self.col('brow', 1, P))
                ctx.stroke()
                continue
            if e == 'wide':
                rx, ry, pr = 0.19 * r, 0.24 * r, 0.075 * r
            elif e == 'squint':
                rx, ry, pr = 0.15 * r, 0.09 * r, 0.08 * r
            elif e == 'tiny':
                rx, ry, pr = 0.2 * r, 0.25 * r, 0.05 * r
            else:
                rx, ry, pr = 0.15 * r, 0.19 * r, 0.09 * r
            ellipse(ctx, ex, ey, rx * sx, ry, self.col('eye', 1, P))
            circle(ctx, ex + lx * rx * 0.45 * sx, ey + ly * ry * 0.4, pr, self.col('pupil', 1, P))
            if e in ('open', 'wide', 'tiny'):
                circle(ctx, ex + lx * rx * 0.45 * sx + pr * 0.35, ey + ly * ry * 0.4 - pr * 0.4,
                       pr * 0.32, (1, 1, 1, 0.9 * P.lit))
            # brows
            by = ey - ry - 0.12 * r
            bw = 0.19 * r * sx
            if P.brows == 'worried':
                a, b = (ex - bw, by + 2), (ex + bw, by - 6)
                if eyes.index((ex, ey, sx)) == 1 or (len(eyes) == 2 and ex > 0 and eyes[0][0] < 0):
                    a, b = (ex - bw, by - 6), (ex + bw, by + 2)
            elif P.brows == 'angry':
                a, b = (ex - bw, by - 5), (ex + bw, by + 4)
                if len(eyes) == 2 and ex > 0 and eyes[0][0] < 0:
                    a, b = (ex - bw, by + 4), (ex + bw, by - 5)
            elif P.brows == 'up':
                a, b = (ex - bw, by - 8), (ex + bw, by - 8)
            else:
                a, b = (ex - bw, by - 2), (ex + bw, by - 2)
            line(ctx, a, b, 4.2, self.col('brow', 1, P))
        # mouth
        mx, my = mpos
        m = P.mouth
        mc = self.col('mouth', 1, P)
        if m == 'smile':
            ctx.new_path()
            ctx.arc(mx, my - 0.12 * r, 0.16 * r, 0.2 * math.pi, 0.8 * math.pi)
            ctx.set_line_width(3.5)
            src(ctx, mc)
            ctx.stroke()
        elif m == 'flat':
            line(ctx, (mx - 0.12 * r, my), (mx + 0.12 * r, my), 3.5, mc)
        elif m == 'frown':
            ctx.new_path()
            ctx.arc(mx, my + 0.12 * r, 0.14 * r, 1.2 * math.pi, 1.8 * math.pi)
            ctx.set_line_width(3.5)
            src(ctx, mc)
            ctx.stroke()
        elif m == 'o':
            ellipse(ctx, mx, my, 0.08 * r, 0.11 * r, mc)
        elif m == 'scream':
            o = 0.6 + 0.4 * P.mouth_open
            ellipse(ctx, mx, my + 0.04 * r, 0.14 * r, 0.22 * r * o, mc)
            ellipse(ctx, mx, my + 0.12 * r * o, 0.08 * r, 0.06 * r * o, mul(hexc('#a33a3a'), P.lit))
        elif m == 'grit':
            rrect(ctx, mx - 0.17 * r, my - 0.06 * r, 0.34 * r, 0.13 * r, 3, self.col('eye', 0.95, P))
            line(ctx, (mx - 0.17 * r, my), (mx + 0.17 * r, my), 1.5, mc)
        if P.sweat > 0:
            sx_, sy_ = eyes[0][0] - 0.45 * r, eyes[0][1] - 0.35 * r + P.sweat * 0.3 * r
            ctx.new_path()
            ctx.move_to(sx_, sy_ - 0.14 * r)
            ctx.curve_to(sx_ + 0.09 * r, sy_, sx_ + 0.07 * r, sy_ + 0.08 * r, sx_, sy_ + 0.08 * r)
            ctx.curve_to(sx_ - 0.07 * r, sy_ + 0.08 * r, sx_ - 0.09 * r, sy_, sx_, sy_ - 0.14 * r)
            src(ctx, (0.62, 0.82, 1.0, 0.9 * P.lit))
            ctx.fill()

    # .............................................................. front view
    def _front(self, ctx, P):
        t = P.t
        tr = P.tremble
        tx = noise(t * 40, 11) * 2.5 * tr
        ty = noise(t * 37, 12) * 2.5 * tr
        hip = (P.hip_dx, -HIP_H + P.hip_dy)
        sh_y = hip[1] - TORSO
        out = {}
        # legs
        if not P.hide_legs:
            for sx in (-1, 1):
                h = (hip[0] + sx * 18, hip[1] + 2)
                ft = (hip[0] + sx * 24, 0 - 8)
                kn = ik2(h, ft, THIGH, SHIN, -sx)
                pc = self.col('pants', 0.9 if sx < 0 else 1, P)
                taper(ctx, h, kn, 25, 21, pc)
                taper(ctx, kn, ft, 21, 17, pc)
                ellipse(ctx, ft[0] + sx * 8, ft[1] + 2, 20, 9, self.col('shoe', 1, P))
        if P.backpack:
            rrect(ctx, hip[0] - 50, sh_y + 18, 100, 120, 18, self._bp(0.6, P))
        tor = [(hip[0] - 37, hip[1] + 6), (hip[0] + 37, hip[1] + 6), (hip[0] + 44, sh_y + 38),
               (hip[0] + 34, sh_y), (hip[0] - 34, sh_y), (hip[0] - 44, sh_y + 38)]
        fill_poly(ctx, tor, self.col('shirt', 1, P))
        if P.sil is None:
            ctx.save()
            poly(ctx, tor)
            ctx.clip()
            fill_poly(ctx, [(hip[0] - 60, hip[1] + 10), (hip[0] - 20, hip[1] + 10), (hip[0] - 30, sh_y - 5),
                            (hip[0] - 60, sh_y - 5)], self.col('shirt_d', 1, P))
            ctx.restore()
            line(ctx, (hip[0] - 37, hip[1] - 2), (hip[0] + 37, hip[1] - 2), 5, self.col('pants', 1.2, P),
                 cairo.LINE_CAP_BUTT)
        if P.backpack:
            for sx in (-1, 1):
                line(ctx, (hip[0] + sx * 26, sh_y + 2), (hip[0] + sx * 24, sh_y + 90), 10, self._bp(0.85, P))
        # neck/head
        hc = (hip[0] + tx * 0.6, sh_y - 48 + P.head_dy + ty * 0.6)
        line(ctx, (hip[0], sh_y + 4), (hip[0], sh_y - 18), 20, self.col('skin_d', 1, P), cairo.LINE_CAP_BUTT)
        self._head_front(ctx, hc, P)
        out['head'] = hc
        # arms
        for sx, hand, k in ((-1, P.hand_b, 0.92), (1, P.hand_f, 1.0)):
            shp = (hip[0] + sx * 38, sh_y + 12)
            if P.hand_mouth:
                hand = (hc[0] - shp[0] + sx * 12, hc[1] - shp[1] + 30)
            elif hand is None:
                hand = (sx * 14, 150)
            else:
                hand = (hand[0] * sx, hand[1])
            tgt = (shp[0] + hand[0] + tx, shp[1] + hand[1] + ty)
            tgt = clamp_reach(shp, tgt, UARM + FARM - 1)
            el = ik2(shp, tgt, UARM, FARM, sx)
            c = self.col('shirt', k, P)
            taper(ctx, shp, el, 18, 16, c)
            taper(ctx, el, tgt, 16, 15, c)
            circle(ctx, tgt[0], tgt[1], 10.5, self.col('skin', 1, P))
            out['hand_r' if sx > 0 else 'hand_l'] = tgt
        return out

    def _head_front(self, ctx, hc, P):
        r = HEAD_R
        x, y = hc
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(R(P.head_tilt))
        for sx in (-1, 1):
            ellipse(ctx, sx * 0.96 * r, 0.1 * r, 0.17 * r, 0.25 * r, self.col('skin_d', 1, P))
        circle(ctx, 0, 0, r, self.col('skin_d', 1, P))
        if P.sil is not None:
            ctx.restore()
            return
        ctx.save()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.clip()
        circle(ctx, 0.12 * r, -0.12 * r, 0.97 * r, self.col('skin', 1, P))
        if self.st.get('hair') is not None:
            hp = [(-1.2 * r, -0.2 * r), (-1.1 * r, -1.2 * r), (1.2 * r, -1.2 * r), (1.1 * r, -0.3 * r),
                  (0.6 * r, -0.55 * r), (0.2 * r, -0.45 * r), (-0.3 * r, -0.6 * r), (-0.8 * r, -0.45 * r)]
            fill_poly(ctx, hp, self.col('hair', 1, P))
        ctx.restore()
        ellipse(ctx, 0.0, 0.16 * r, 0.09 * r, 0.06 * r, self.col('skin_d', 0.9, P))
        self._face(ctx, P, [(-0.34 * r, -0.08 * r, 1.0), (0.34 * r, -0.08 * r, 1.0)], (0, 0.46 * r))
        if P.rim is not None:
            ctx.save()
            ctx.arc(0, 0, r, 0, 2 * math.pi)
            ctx.clip()
            ctx.new_path()
            ctx.arc(0, 0, r, 0, 2 * math.pi)
            ctx.arc_negative(-0.1 * r, 0.03 * r, r, 2 * math.pi, 0)
            src(ctx, P.rim)
            ctx.fill()
            ctx.restore()
        ctx.restore()


HERO = Person(HERO_STYLE)


# ---------------------------------------------------------------- monster
class MPose(dict):
    DEF = dict(view='side', torso=32.0, torso_len=380, neck=55.0, head=10.0, mouth=0.0,
               hand_b=(140, 560), hand_f=(200, 600), foot_b=(-60, 640), foot_f=(80, 640),
               curl=0.3, curl_b=None, finger_spread=1.0, t=0.0, body=hexc('#1a1b22'), rim=None, rim_off=(6, -3),
               lit=1.0, sil=False, drool=0.0, teeth=1.0, breathe=1.0, jaw_jitter=0.0, red_mouth=1.0, elbows_out=False)

    def __getattr__(self, k):
        if k in self:
            return self[k]
        return MPose.DEF[k]

    def __setattr__(self, k, v):
        self[k] = v


M_THIGH, M_SHIN, M_META = 300, 310, 150
M_UARM, M_FARM = 330, 330
FINGER = 120


class Monster:
    """Tall eyeless creature. Origin = hip joint. Side view faces +x."""

    def draw(self, ctx, x, y, s, MP, facing=1):
        MP = MPose(MP)
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(s * facing, s)
        out = {}
        if MP.rim is not None:
            ctx.save()
            ctx.translate(*MP.rim_off)
            self._body(ctx, MP, MP.rim, rim_pass=True)
            ctx.restore()
        out = self._body(ctx, MP, MP.body, rim_pass=False)
        ctx.restore()
        res = {}
        for k, (lx, ly) in out.items():
            res[k] = (x + lx * s * facing, y + ly * s)
        return res

    def _c(self, base, k, MP, rim_pass):
        if rim_pass:
            return base
        return mul(base, k * MP.lit)

    def _body(self, ctx, MP, base, rim_pass):
        t = MP.t
        C = lambda k: self._c(base, k, MP, rim_pass)
        out = {}
        if MP.view == 'front':
            return self._front(ctx, MP, base, rim_pass)
        br = math.sin(t * 2.2) * 6 * MP.breathe
        ta = R(MP.torso)
        L = MP.torso_len
        # spine points
        ux, uy = math.sin(ta), -math.cos(ta)
        vx, vy = -uy, ux
        hip = (0, 0)
        chest = (ux * L, uy * L + br)
        sh = (chest[0] - vx * 10, chest[1] - vy * 10)
        # back limbs first
        sh_b = (sh[0] - 14, sh[1] + 6)
        self._leg(ctx, (hip[0] - 10, hip[1]), MP.foot_b, C(0.62))
        self._arm(ctx, sh_b, MP.hand_b, C(0.62), MP, MP.curl_b if MP.curl_b is not None else MP.curl, back=True,
                  rim_pass=rim_pass)
        # torso polygon (thin, ribbed, with a hump)
        def T(v, u):
            return (hip[0] + vx * v + ux * u, hip[1] + vy * v + uy * u + br * u / L)
        tor = [T(-42, -10), T(36, -10), T(30, 90), T(44, 200), T(62, 290), T(48, L + 10), T(-30, L + 28),
               T(-70, L - 40), T(-66, 220), T(-48, 120)]
        ctx.new_path()
        ctx.move_to(*tor[0])
        for i in range(1, len(tor)):
            a, b = tor[i - 1], tor[i]
            ctx.curve_to(a[0] + (b[0] - a[0]) * 0.3, a[1] + (b[1] - a[1]) * 0.3,
                         a[0] + (b[0] - a[0]) * 0.7, a[1] + (b[1] - a[1]) * 0.7, b[0], b[1])
        ctx.close_path()
        src(ctx, C(1.0))
        ctx.fill()
        if not rim_pass and not MP.sil:
            # ribs and spine ridges
            for i in range(5):
                u = 190 + i * 34
                a = T(50, u)
                b = T(-46, u + 22)
                ctx.new_path()
                ctx.move_to(*a)
                ctx.curve_to(*T(20, u - 12), *T(-20, u + 2), *b)
                ctx.set_line_width(5)
                src(ctx, mul(base, 1.55 * MP.lit))
                ctx.stroke()
            for i in range(7):
                u = 60 + i * 48
                p = T(-58 - 6 * math.sin(i), u)
                fill_poly(ctx, [T(-50, u - 16), (p[0] - vx * 18, p[1] - vy * 18), T(-50, u + 16)], C(0.8))
        # neck + head
        na = ta + R(MP.neck)
        neck_base = T(10, L - 6)
        nl = 120
        nt = (neck_base[0] + math.sin(na) * nl, neck_base[1] - math.cos(na) * nl)
        taper(ctx, neck_base, nt, 46, 34, C(0.9))
        self._head_side(ctx, nt, R(22) + R(MP.head) + (ta + R(MP.neck) - R(87)) * 0.35, MP, base, rim_pass)
        out['head'] = nt
        out['chest'] = chest
        # front limbs
        self._leg(ctx, (hip[0] + 10, hip[1] + 4), MP.foot_f, C(1.0))
        sh_f = (sh[0] + 6, sh[1] + 10)
        hand = self._arm(ctx, sh_f, MP.hand_f, C(1.0), MP, MP.curl, back=False, rim_pass=rim_pass)
        out['hand'] = hand
        return out

    def _leg(self, ctx, hip, toe, c):
        hock = (toe[0] - 70, toe[1] - 120)
        hock = clamp_reach(hip, hock, M_THIGH + M_SHIN - 2)
        knee = ik2(hip, hock, M_THIGH, M_SHIN, 1)
        taper(ctx, hip, knee, 118, 64, c)
        taper(ctx, knee, hock, 62, 34, c)
        taper(ctx, hock, toe, 34, 22, c)
        # long clawed toes
        for i, a in enumerate((-0.25, 0.05, 0.3)):
            d = (math.cos(a) * 60, math.sin(a) * 18 + 6)
            tip = (toe[0] + d[0], toe[1] + d[1])
            taper(ctx, toe, tip, 14, 3, c, round_ends=False)

    def _arm(self, ctx, sh, hand, c, MP, curl, back, rim_pass):
        tgt = (hand[0], hand[1])
        tgt = clamp_reach(sh, tgt, M_UARM + M_FARM - 2)
        el = ik2(sh, tgt, M_UARM, M_FARM, 1)
        taper(ctx, sh, el, 40, 26, c)
        taper(ctx, el, tgt, 26, 18, c)
        # bony elbow spike
        dx, dy = el[0] - sh[0], el[1] - sh[1]
        d = math.hypot(dx, dy) or 1
        fill_poly(ctx, [(el[0] - dy / d * 12, el[1] + dx / d * 12), (el[0] + dx / d * 30, el[1] + dy / d * 30),
                        (el[0] + dy / d * 12, el[1] - dx / d * 12)], c)
        # hand + fingers
        fa = math.atan2(tgt[1] - el[1], tgt[0] - el[0])
        palm = (tgt[0] + math.cos(fa) * 26, tgt[1] + math.sin(fa) * 26)
        taper(ctx, tgt, palm, 30, 34, c)
        t = MP.t
        for i in range(4):
            spread = (i - 1.5) * 0.24 * MP.finger_spread
            tw = noise(t * 3 + i * 7, 20 + i + (5 if back else 0)) * 0.25
            a1 = fa + spread
            c1 = curl * 0.9 + tw
            p1 = (palm[0] + math.cos(a1) * FINGER * 0.55, palm[1] + math.sin(a1) * FINGER * 0.55)
            a2 = a1 + c1
            p2 = (p1[0] + math.cos(a2) * FINGER * 0.5, p1[1] + math.sin(a2) * FINGER * 0.5)
            a3 = a2 + c1 * 0.9
            p3 = (p2[0] + math.cos(a3) * FINGER * 0.38, p2[1] + math.sin(a3) * FINGER * 0.38)
            taper(ctx, palm, p1, 11, 9, c)
            taper(ctx, p1, p2, 9, 7, c)
            taper(ctx, p2, p3, 7, 1.5, c, round_ends=False)
        return palm

    def _teeth_row(self, ctx, a, b, n, h, direction, c, jitter=0.0, seed=0):
        """Triangular teeth along segment a-b pointing to `direction` side (+1 = left normal)."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d * direction, dx / d * direction
        for i in range(n):
            f0, f1 = i / n, (i + 1) / n
            p0 = (a[0] + dx * f0, a[1] + dy * f0)
            p1 = (a[0] + dx * f1, a[1] + dy * f1)
            m = (a[0] + dx * (f0 + f1) / 2, a[1] + dy * (f0 + f1) / 2)
            hh = h * (0.75 + 0.5 * abs(noise(i * 1.3, seed)))
            tip = (m[0] + nx * hh + dx / d * noise(i, seed + 3) * 4, m[1] + ny * hh + dy / d * noise(i, seed + 3) * 4)
            fill_poly(ctx, [p0, tip, p1], c)

    def _head_side(self, ctx, base_pt, ang, MP, base, rim_pass):
        """Elongated eyeless head; `ang` is the head's up-axis angle from vertical."""
        C = lambda k: self._c(base, k, MP, rim_pass)
        ctx.save()
        ctx.translate(*base_pt)
        ctx.rotate(ang)
        # head local: +y down, head extends upward (-y), face toward +x
        o = clamp(MP.mouth) + noise(MP.t * 20, 9) * MP.jaw_jitter
        jaw_ang = R(50) * o
        hinge = (-34, -40)
        cx, cy, rx, ry = 22, -150, 78, 175
        tip_u = (112, -96)    # mouth line front point on skull
        # upper skull
        ctx.save()
        poly(ctx, [(-200, -500), (300, -500), (300, tip_u[1] + (tip_u[1] - hinge[1]) * 0.0), tip_u, hinge,
                   (-200, hinge[1] + 30)])
        ctx.clip()
        ellipse(ctx, cx, cy, rx, ry, C(1.05), R(-12))
        ctx.restore()
        # mouth interior
        jp = rot(tip_u, jaw_ang, hinge)
        if o > 0.02 and not rim_pass:
            fill_poly(ctx, [hinge, tip_u, (tip_u[0] + 12, (tip_u[1] + jp[1]) / 2), jp], hexc('#190406'))
            # inner rows of teeth (several rows!)
            for k, (sc, cc) in enumerate(((0.75, hexc('#9e968a')), (0.55, hexc('#6f675e')))):
                ia = (hinge[0] + (tip_u[0] - hinge[0]) * (1 - sc), hinge[1] + (tip_u[1] - hinge[1]) * (1 - sc) + 10 + k * 8)
                self._teeth_row(ctx, ia, tip_u, 8 - k * 2, 18 * sc, 1, mul(cc, MP.lit), seed=10 + k)
                ja = (hinge[0] + (jp[0] - hinge[0]) * (1 - sc), hinge[1] + (jp[1] - hinge[1]) * (1 - sc) - 10 - k * 8)
                self._teeth_row(ctx, ja, jp, 8 - k * 2, 18 * sc, -1, mul(cc, MP.lit), seed=20 + k)
        # jaw
        ctx.save()
        ctx.translate(*hinge)
        ctx.rotate(jaw_ang)
        ctx.translate(-hinge[0], -hinge[1])
        ctx.save()
        poly(ctx, [(-200, hinge[1] + 30), hinge, tip_u, (300, tip_u[1]), (300, 300), (-200, 300)])
        ctx.clip()
        ellipse(ctx, cx, cy, rx, ry, C(0.9), R(-12))
        ctx.restore()
        if not rim_pass and MP.teeth > 0:
            self._teeth_row(ctx, (hinge[0] + 20, hinge[1] + 4), (tip_u[0] - 4, tip_u[1] + 4), 9, 26, -1,
                            mul(hexc('#e7e0cf'), MP.lit), seed=2)
        ctx.restore()
        if not rim_pass and MP.teeth > 0:
            self._teeth_row(ctx, (hinge[0] + 20, hinge[1] - 4), (tip_u[0] - 4, tip_u[1] - 4), 9, 28, 1,
                            mul(hexc('#efe8d6'), MP.lit), seed=1)
        if not rim_pass and not MP.sil:
            # skull ridges where eyes would be (smooth, eyeless)
            ctx.new_path()
            ctx.move_to(60, -180)
            ctx.curve_to(90, -150, 100, -130, 104, -110)
            ctx.set_line_width(6)
            src(ctx, mul(base, 1.6 * MP.lit))
            ctx.stroke()
            ellipse(ctx, 40, -175, 34, 16, mul(base, 0.6 * MP.lit), R(-20))
            if MP.drool > 0 and o > 0.05:
                for i, fx in enumerate((0.3, 0.6, 0.8)):
                    p = (hinge[0] + (tip_u[0] - hinge[0]) * fx, hinge[1] + (tip_u[1] - hinge[1]) * fx)
                    q = rot(p, jaw_ang, hinge)
                    sag = 30 + 20 * math.sin(MP.t * 2 + i)
                    ctx.new_path()
                    ctx.move_to(*p)
                    ctx.curve_to(p[0], p[1] + sag, q[0], q[1] + sag, q[0], q[1])
                    ctx.set_line_width(2.5)
                    src(ctx, (0.75, 0.8, 0.82, 0.35 * MP.drool * MP.lit))
                    ctx.stroke()
        ctx.restore()

    # ................................................................ front view
    def _front(self, ctx, MP, base, rim_pass):
        C = lambda k: self._c(base, k, MP, rim_pass)
        t = MP.t
        br = math.sin(t * 2.2) * 6 * MP.breathe
        L = MP.torso_len
        out = {}
        chest_y = -L + br
        # legs (knees bent outward - unnatural)
        for sx in (-1, 1):
            hp = (sx * 40, 0)
            ft = (sx * 150, 640)
            hock = (sx * 120, 520)
            kn = ik2(hp, hock, M_THIGH, M_SHIN, sx)
            taper(ctx, hp, kn, 110, 60, C(0.75 if sx < 0 else 0.9))
            taper(ctx, kn, hock, 58, 32, C(0.75 if sx < 0 else 0.9))
            taper(ctx, hock, ft, 30, 20, C(0.75 if sx < 0 else 0.9))
            for a in (-0.4, 0.0, 0.4):
                taper(ctx, ft, (ft[0] + sx * 30 + math.sin(a) * 40, ft[1] + 22), 12, 3, C(0.8), round_ends=False)
        # torso
        tor = [(-48, 10), (48, 10), (40, -120), (66, -220), (100, chest_y + 30), (70, chest_y - 10),
               (-70, chest_y - 10), (-100, chest_y + 30), (-66, -220), (-40, -120)]
        ctx.new_path()
        ctx.move_to(*tor[0])
        for i in range(1, len(tor)):
            a, b = tor[i - 1], tor[i]
            ctx.curve_to(a[0] + (b[0] - a[0]) * 0.3, a[1] + (b[1] - a[1]) * 0.3,
                         a[0] + (b[0] - a[0]) * 0.7, a[1] + (b[1] - a[1]) * 0.7, b[0], b[1])
        ctx.close_path()
        src(ctx, C(1.0))
        ctx.fill()
        if not rim_pass and not MP.sil:
            for i in range(5):
                y = chest_y + 60 + i * 34
                for sx in (-1, 1):
                    ctx.new_path()
                    ctx.move_to(sx * 6, y)
                    ctx.curve_to(sx * 40, y - 14, sx * 70, y, sx * 84, y + 22)
                    ctx.set_line_width(5)
                    src(ctx, mul(base, 1.55 * MP.lit))
                    ctx.stroke()
            line(ctx, (0, chest_y + 40), (0, -40), 4, mul(base, 0.6 * MP.lit))
        # arms
        hands = {}
        for sx, hand, k in ((-1, MP.hand_b, 0.85), (1, MP.hand_f, 1.0)):
            sh = (sx * 92, chest_y + 22)
            tgt = (hand[0] if sx > 0 else -hand[0], hand[1])
            tgt = (tgt[0], tgt[1])
            hands[sx] = self._arm_front(ctx, sh, tgt, C(k), MP, sx)
        out['hand_l'] = hands[-1]
        out['hand_r'] = hands[1]
        # neck + head
        nb = (0, chest_y - 4)
        hb = (math.sin(R(MP.head)) * 30, chest_y - 90)
        taper(ctx, nb, hb, 50, 40, C(0.9))
        self._head_front(ctx, hb, MP, base, rim_pass)
        out['head'] = hb
        return out

    def _arm_front(self, ctx, sh, tgt, c, MP, sx):
        tgt = clamp_reach(sh, tgt, M_UARM + M_FARM - 2)
        el = ik2(sh, tgt, M_UARM, M_FARM, sx if MP.elbows_out else -sx)
        taper(ctx, sh, el, 40, 26, c)
        taper(ctx, el, tgt, 26, 18, c)
        fa = math.atan2(tgt[1] - el[1], tgt[0] - el[0])
        palm = (tgt[0] + math.cos(fa) * 26, tgt[1] + math.sin(fa) * 26)
        taper(ctx, tgt, palm, 30, 34, c)
        for i in range(4):
            spread = (i - 1.5) * 0.22 * MP.finger_spread
            tw = noise(MP.t * 3 + i * 7, 30 + i + sx) * 0.25
            a1 = fa + spread
            cu = (MP.curl * 0.8 + tw) * -sx
            p1 = (palm[0] + math.cos(a1) * FINGER * 0.55, palm[1] + math.sin(a1) * FINGER * 0.55)
            p2 = (p1[0] + math.cos(a1 + cu) * FINGER * 0.5, p1[1] + math.sin(a1 + cu) * FINGER * 0.5)
            p3 = (p2[0] + math.cos(a1 + cu * 1.9) * FINGER * 0.38, p2[1] + math.sin(a1 + cu * 1.9) * FINGER * 0.38)
            taper(ctx, palm, p1, 11, 9, c)
            taper(ctx, p1, p2, 9, 7, c)
            taper(ctx, p2, p3, 7, 1.5, c, round_ends=False)
        return palm

    def _head_front(self, ctx, hb, MP, base, rim_pass):
        C = lambda k: self._c(base, k, MP, rim_pass)
        o = clamp(MP.mouth) + noise(MP.t * 20, 9) * MP.jaw_jitter
        ctx.save()
        ctx.translate(*hb)
        ctx.rotate(R(MP.head) * 0.5)
        rx, ry = 82, 190
        cy = -150
        # skull
        ellipse(ctx, 0, cy, rx, ry, C(1.05))
        if rim_pass or MP.sil:
            ctx.restore()
            return
        # smooth eyeless face: brow ridge shading
        ellipse(ctx, 0, cy - 40, 60, 26, mul(base, 0.65 * MP.lit))
        ctx.new_path()
        ctx.move_to(-62, cy - 20)
        ctx.curve_to(-30, cy - 40, 30, cy - 40, 62, cy - 20)
        ctx.set_line_width(5)
        src(ctx, mul(base, 1.7 * MP.lit))
        ctx.stroke()
        # mouth: from a jagged seam to a huge ring of teeth
        my = cy + 70
        mrx = 66
        mry = 6 + 105 * o
        if o < 0.05:
            pts = []
            for i in range(17):
                x = -mrx + i * mrx * 2 / 16
                y = my + (5 if i % 2 else -5) * MP.teeth
                pts.append((x, y))
            polyline(ctx, pts, 3, mul(hexc('#e8e0cc'), MP.lit))
            line(ctx, (-mrx - 8, my), (mrx + 8, my), 3, mul(hexc('#2a0a0c'), MP.lit))
        else:
            ellipse(ctx, 0, my, mrx + 8, mry + 8, mul(hexc('#5a1218'), MP.lit * MP.red_mouth + 0.2))
            g = cairo.RadialGradient(0, my, 0, 0, my, max(mrx, mry))
            g.add_color_stop_rgba(0, 0, 0, 0, 1)
            g.add_color_stop_rgba(0.7, 0.12 * MP.lit, 0.01, 0.02, 1)
            g.add_color_stop_rgba(1, 0.3 * MP.lit, 0.04, 0.06, 1)
            ellipse_path(ctx, 0, my, mrx, mry)
            ctx.set_source(g)
            ctx.fill()
            # concentric rows of teeth pointing inward
            for k, sc in enumerate((1.0, 0.78, 0.58)):
                n = 22 - k * 4
                cc = mul(hexc('#efe8d6'), MP.lit * (1 - k * 0.25))
                for i in range(n):
                    a0 = 2 * math.pi * i / n + k * 0.13
                    a1 = 2 * math.pi * (i + 1) / n + k * 0.13
                    am = (a0 + a1) / 2
                    p0 = (math.cos(a0) * mrx * sc, my + math.sin(a0) * mry * sc)
                    p1 = (math.cos(a1) * mrx * sc, my + math.sin(a1) * mry * sc)
                    hl = 0.32 + 0.12 * abs(noise(i * 1.7, k))
                    tip = (math.cos(am) * mrx * sc * (1 - hl), my + math.sin(am) * mry * sc * (1 - hl))
                    fill_poly(ctx, [p0, tip, p1], cc)
            if MP.drool > 0:
                for i, fx in enumerate((-0.5, 0.1, 0.55)):
                    x = fx * mrx
                    sag = 20 + 15 * math.sin(MP.t * 2 + i)
                    ctx.new_path()
                    ctx.move_to(x, my - mry * 0.8)
                    ctx.curve_to(x - 6, my, x + 6, my + mry * 0.6, x + 3, my + mry * 0.85 + sag * 0.2)
                    ctx.set_line_width(3)
                    src(ctx, (0.75, 0.8, 0.82, 0.3 * MP.drool * MP.lit))
                    ctx.stroke()
        ctx.restore()


MONSTER = Monster()


def monster_walk(t, speed=0.35, stride=170, seed=0):
    """Slow lurching walk. Returns (MPose fields, hip_dx_offset, hip_dy)."""
    p = t * speed + seed * 0.37
    a = math.sin(p * 2 * math.pi)
    b = math.cos(p * 2 * math.pi)
    hip_dy = -abs(b) * 18
    lift_f = max(0, b) * 60
    lift_b = max(0, -b) * 60
    foot_f = (40 + a * stride, 640 - hip_dy - lift_f)
    foot_b = (-20 - a * stride, 640 - hip_dy - lift_b)
    hand_f = (150 - a * 120, 560 + abs(a) * 30)
    hand_b = (110 + a * 110, 540 + abs(a) * 30)
    head = jerk(t, 1.6, seed + 4) * 18
    return dict(foot_f=foot_f, foot_b=foot_b, hand_f=hand_f, hand_b=hand_b, head=head,
                torso=30 + noise(t * 0.7, seed) * 6, neck=48 + jerk(t, 1.2, seed + 9) * 10), hip_dy


# ---------------------------------------------------------------- dog
def draw_dog(ctx, x, y, s, t, run=True, facing=1, lit=1.0, phase=0.0):
    body = mul(hexc('#a8733f'), lit)
    dark = mul(hexc('#7a4f28'), lit)
    light = mul(hexc('#dcb98d'), lit)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s * facing, s)
    p = t * 3.2 + phase if run else 0
    bob = -abs(math.sin(p * math.pi * 2)) * 8 if run else 0
    ctx.translate(0, bob)
    # tail
    tw = math.sin(t * 14) * 10
    ctx.new_path()
    ctx.move_to(-46, -64)
    ctx.curve_to(-64, -76, -70, -96 + tw, -62, -104 + tw)
    ctx.set_line_width(9)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    src(ctx, body)
    ctx.stroke()
    # legs
    for i, (lx, ph, c) in enumerate(((-34, 0.5, dark), (30, 0.0, dark), (-26, 0.0, body), (38, 0.5, body))):
        a = math.sin((p + ph) * 2 * math.pi) * (0.6 if run else 0)
        top = (lx, -52)
        knee = (lx + math.sin(a) * 22, -30)
        foot = (lx + math.sin(a) * 34, -4 - max(0, math.cos((p + ph) * 2 * math.pi)) * (10 if run else 0))
        taper(ctx, top, knee, 12, 10, c)
        taper(ctx, knee, foot, 10, 9, c)
        ellipse(ctx, foot[0] + 4, foot[1] + 2, 8, 5, c)
    # body
    rrect(ctx, -54, -80, 108, 40, 20, body)
    ellipse(ctx, 6, -48, 34, 10, light)
    # head
    hx, hy = 56, -94
    circle(ctx, hx, hy, 24, body)
    rrect(ctx, hx + 10, hy - 4, 34, 22, 9, light)
    circle(ctx, hx + 42, hy + 2, 6, hexc('#151010'))
    ellipse(ctx, hx - 8, hy - 2, 9, 20, dark, R(15 + math.sin(t * 9) * 8))
    circle(ctx, hx + 8, hy - 8, 5, hexc('#f4efe6'))
    circle(ctx, hx + 9.5, hy - 8, 3, hexc('#111111'))
    if run:
        ctx.new_path()
        ctx.arc(hx + 30, hy + 16, 6, 0, math.pi)
        src(ctx, hexc('#c2455a'))
        ctx.fill()
    ctx.restore()


# ---------------------------------------------------------------- props
def draw_backpack(ctx, x, y, s, lit=1.0, open_=1.0):
    c = mul(hexc('#4a5a40'), lit)
    d = mul(hexc('#33402c'), lit)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    rrect(ctx, -150, -260, 300, 300, 60, c)
    rrect(ctx, -110, -60, 220, 90, 26, d)
    line(ctx, (-110, -15), (110, -15), 4, mul(hexc('#222a1e'), lit))
    # opening
    ow = 260 * open_
    ellipse(ctx, 0, -250, ow / 2, 34 * open_ + 4, mul(hexc('#141a12'), lit))
    rrect(ctx, -60, -310, 120, 40, 18, d)
    line(ctx, (-150, -200), (-150, -40), 10, d)
    ctx.restore()


def draw_bottle(ctx, x, y, s, ang=0, lit=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    rrect(ctx, -26, -60, 52, 130, 18, (0.45 * lit, 0.7 * lit, 0.95 * lit, 0.85))
    rect(ctx, -26, -20, 52, 36, mul(hexc('#2c6fb8'), lit))
    rrect(ctx, -14, -84, 28, 28, 6, mul(hexc('#1f4f8f'), lit))
    rect(ctx, -18, -54, 8, 110, (1, 1, 1, 0.25 * lit))
    ctx.restore()


def draw_can(ctx, x, y, s, ang=0, lit=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    rrect(ctx, -40, -50, 80, 100, 10, mul(hexc('#9aa0a6'), lit))
    rect(ctx, -40, -30, 80, 60, mul(hexc('#c0392b'), lit))
    circle(ctx, 0, 0, 16, mul(hexc('#f1c40f'), lit))
    rect(ctx, -40, -50, 80, 8, mul(hexc('#cfd4d8'), lit))
    ctx.restore()


def draw_medkit(ctx, x, y, s, ang=0, lit=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    rrect(ctx, -60, -42, 120, 84, 12, mul(hexc('#d63a3a'), lit))
    rrect(ctx, -22, -60, 44, 22, 6, mul(hexc('#8e2424'), lit))
    rect(ctx, -10, -30, 20, 60, mul(hexc('#f4f1ea'), lit))
    rect(ctx, -30, -10, 60, 20, mul(hexc('#f4f1ea'), lit))
    ctx.restore()


def draw_flashlight(ctx, x, y, s, ang=0, lit=1.0, on=False):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    rrect(ctx, -70, -16, 110, 32, 8, mul(hexc('#2b2f38'), lit))
    fill_poly(ctx, [(40, -16), (70, -28), (70, 28), (40, 16)], mul(hexc('#3a3f4a'), lit))
    rect(ctx, 66, -28, 8, 56, mul(hexc('#e8e4cf'), lit) if not on else hexc('#fff6c8'))
    rect(ctx, -20, -20, 18, 8, mul(hexc('#c0392b'), lit))
    ctx.restore()


def draw_rebar(ctx, a, b, w=16, lit=1.0):
    c = mul(hexc('#7a4a2c'), lit)
    d = mul(hexc('#4e2e1a'), lit)
    line(ctx, a, b, w, c, cairo.LINE_CAP_BUTT)
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    n = int(L / 22)
    for i in range(1, n):
        f = i / n
        p = (a[0] + dx * f, a[1] + dy * f)
        line(ctx, (p[0] - nx * w * 0.6 + dx / L * 5, p[1] - ny * w * 0.6 + dy / L * 5),
             (p[0] + nx * w * 0.6 - dx / L * 5, p[1] + ny * w * 0.6 - dy / L * 5), 3.5, d)
    line(ctx, (a[0] + nx * w * 0.25, a[1] + ny * w * 0.25), (b[0] + nx * w * 0.25, b[1] + ny * w * 0.25), 3,
         mul(hexc('#a8714a'), lit))
