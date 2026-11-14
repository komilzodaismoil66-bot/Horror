"""'Поезд в 03:17' characters: chunky flat 2D people (round head, bowl hair, dot eyes, tube limbs)."""
import math
import cairo
from engine import *
from characters import Pose, walk_pose, run_pose, sneak_pose

R = math.radians

HERO3 = dict(
    skin=hexc('#c89a72'), skin_d=hexc('#a57a55'), hair=hexc('#eceef4'), hair_d=hexc('#c3c7d6'),
    top=hexc('#5aa6e0'), top_d=hexc('#3f84bf'), pants=hexc('#17191f'), pants_d=hexc('#0f1014'),
    shoe=hexc('#0a0b0e'), eye=hexc('#f4f2ea'), pupil=hexc('#111111'), mouth=hexc('#4a2418'), brow=hexc('#d8dbe6'),
    hood=True, pocket=True)

PASSENGERS = [
    dict(HERO3, skin=hexc('#d9b394'), skin_d=hexc('#b48d6e'), hair=hexc('#2a221c'), hair_d=hexc('#1b1612'),
         top=hexc('#4d5560'), top_d=hexc('#3a4048'), pants=hexc('#2a2c33'), brow=hexc('#2a221c'), hood=False,
         pocket=False),
    dict(HERO3, skin=hexc('#b98a64'), skin_d=hexc('#93694a'), hair=hexc('#5a4030'), hair_d=hexc('#3e2c20'),
         top=hexc('#6a3e3a'), top_d=hexc('#4f2c29'), pants=hexc('#24262c'), brow=hexc('#3e2c20'), hood=False,
         pocket=False),
    dict(HERO3, skin=hexc('#e2c0a0'), skin_d=hexc('#bd9a7c'), hair=hexc('#8c8c90'), hair_d=hexc('#6c6c70'),
         top=hexc('#3e5546'), top_d=hexc('#2d3f33'), pants=hexc('#2c2a26'), brow=hexc('#6c6c70'), hood=False,
         pocket=False),
    dict(HERO3, skin=hexc('#a77a58'), skin_d=hexc('#845d40'), hair=hexc('#15131a'), hair_d=hexc('#0d0c10'),
         top=hexc('#6b6250'), top_d=hexc('#514a3c'), pants=hexc('#1e2026'), brow=hexc('#15131a'), hood=False,
         pocket=False),
    dict(HERO3, skin=hexc('#d4aa86'), skin_d=hexc('#ad8565'), hair=None, hair_d=None,
         top=hexc('#3a4058'), top_d=hexc('#2b3044'), pants=hexc('#2a2a2e'), brow=hexc('#4a3a30'), hood=False,
         pocket=False),
    dict(HERO3, skin=hexc('#c79a7a'), skin_d=hexc('#a37a5c'), hair=hexc('#7a4a26'), hair_d=hexc('#5a361c'),
         top=hexc('#575a5e'), top_d=hexc('#434548'), pants=hexc('#25272c'), brow=hexc('#5a361c'), hood=False,
         pocket=False),
]

HR = 54                 # head radius
THIGH, SHIN = 95, 92
HIP = 195
TORSO = 150
UA, FA = 82, 80
LEGW, ARMW, HANDR = 34, 27, 13.5


class Toon:
    def __init__(self, style=None):
        self.st = style or HERO3

    def c(self, name, k, P):
        if P.sil is not None:
            return P.sil
        col = self.st.get(name)
        if col is None:
            return None
        lit = P.lit
        if P.get('pale', 0) > 0:
            col = mix(col, hexc('#9aa6b8'), P.pale)
        return mul(col, k * lit)

    def draw(self, ctx, x, y, s, P):
        P = Pose(P)
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(s, s)
        f = P.facing
        if f in (1, -1):
            if f < 0:
                ctx.scale(-1, 1)
            out = self._side(ctx, P)
        elif f == 2:
            out = self._back(ctx, P)
        else:
            out = self._front(ctx, P)
        ctx.restore()
        ff = -1 if f == -1 else 1
        res = {}
        for k, v in out.items():
            res[k] = (x + v[0] * s * ff, y + v[1] * s) if isinstance(v, tuple) else v
        return res

    # ------------------------------------------------------------ parts
    def _arm(self, ctx, sh, hand, bend, k, P, front_arm=False, tremble=(0, 0)):
        tgt = (sh[0] + hand[0] + tremble[0], sh[1] + hand[1] + tremble[1])
        tgt = clamp_reach(sh, tgt, UA + FA - 1)
        el = ik2(sh, tgt, UA, FA, bend)
        cc = self.c('top', k, P)
        taper(ctx, sh, el, ARMW, ARMW - 2, cc)
        taper(ctx, el, tgt, ARMW - 2, ARMW - 3, cc)
        if front_arm and P.get('watch'):
            d = math.atan2(tgt[1] - el[1], tgt[0] - el[0])
            wp = (tgt[0] - math.cos(d) * 14, tgt[1] - math.sin(d) * 14)
            ctx.save()
            ctx.translate(*wp)
            ctx.rotate(d)
            rect(ctx, -6, -ARMW / 2 - 1, 12, ARMW + 2, mul(hexc('#1a1a1e'), P.lit))
            ctx.restore()
            circle(ctx, wp[0], wp[1], 10, mul(hexc('#2a2a30'), P.lit))
            circle(ctx, wp[0], wp[1], 7, (0.9, 0.25, 0.2, 1) if P.get('watch_glow') else mul(hexc('#cfd6e0'), P.lit))
        circle(ctx, tgt[0], tgt[1], HANDR, self.c('skin', k, P))
        return el, tgt

    def _leg(self, ctx, hip, th, kn, k, P):
        a = R(th)
        knee = (hip[0] + THIGH * math.sin(a), hip[1] + THIGH * math.cos(a))
        b = a - R(kn)
        ankle = (knee[0] + SHIN * math.sin(b), knee[1] + SHIN * math.cos(b))
        pc = self.c('pants', k, P)
        taper(ctx, hip, knee, LEGW + 2, LEGW, pc)
        taper(ctx, knee, ankle, LEGW, LEGW + 3, pc)       # loose jeans: slightly wider at the bottom
        ctx.save()
        ctx.translate(*ankle)
        rrect(ctx, -14, -4, 50, 20, 9, self.c('shoe', k, P))
        ctx.restore()
        return ankle

    def _torso_side(self, ctx, hip, lean, P):
        ctx.save()
        ctx.translate(*hip)
        ctx.rotate(lean)
        rrect(ctx, -38, -TORSO - 4, 76, TORSO + 14, 20, self.c('top', 1, P))
        if P.sil is None:
            ctx.save()
            rrect_path(ctx, -38, -TORSO - 4, 76, TORSO + 14, 20)
            ctx.clip()
            rect(ctx, -60, -TORSO - 10, 34, TORSO + 30, self.c('top_d', 1, P))
            if self.st.get('pocket'):
                rrect(ctx, 4, -64, 36, 40, 6, self.c('top_d', 1, P))
            rect(ctx, -60, -2, 120, 12, self.c('top_d', 0.95, P))      # hem
            ctx.restore()
            if self.st.get('hood'):
                ellipse(ctx, -24, -TORSO + 2, 30, 24, self.c('top_d', 1, P))
                line(ctx, (18, -TORSO + 8), (20, -TORSO + 48), 3, self.c('hair', 0.9, P) or (1, 1, 1, 1))
        ctx.restore()

    def _hair_side(self, ctx, P, hd=0.0):
        r = HR
        if self.st.get('hair') is None:
            return
        y0 = -0.18 * r + hd * 0.3 * r
        pts = [(-1.3 * r, 0.32 * r), (-1.3 * r, -1.3 * r), (1.3 * r, -1.3 * r), (1.3 * r, y0 - 0.22 * r),
               (0.95 * r, y0 - 0.22 * r)]
        # short spiky fringe
        for i in range(6):
            x = 0.95 * r - i * 0.24 * r
            pts.append((x - 0.06 * r, y0 + (0.12 * r if i % 2 == 0 else -0.02 * r)))
        pts += [(-0.45 * r, y0 + 0.02 * r), (-0.62 * r, 0.32 * r)]
        fill_poly(ctx, pts, self.c('hair', 1, P))
        fill_poly(ctx, [(-1.3 * r, -1.3 * r), (-0.2 * r, -1.3 * r), (-0.6 * r, -0.4 * r), (-1.3 * r, 0.2 * r)],
                  self.c('hair_d', 1, P))

    def _eyes(self, ctx, P, pts, sxs=(1, 1)):
        r = HR
        e = P.eyes
        if P.blink and e in ('open', 'wide') and (P.t + 0.6) % 3.6 < 0.12:
            e = 'closed'
        lx, ly = P.look
        for (ex, ey), sx in zip(pts, sxs):
            if e == 'closed':
                ctx.new_path()
                ctx.save()
                ctx.translate(ex, ey)
                ctx.scale(sx, 1)
                ctx.arc(0, 0, 0.11 * r, 0.15 * math.pi, 0.85 * math.pi)
                ctx.restore()
                ctx.set_line_width(3.5)
                src(ctx, self.c('pupil', 1, P))
                ctx.stroke()
                continue
            if e == 'squeeze':          # >  < : eyes squeezed shut while yelling
                d = 1 if ex < 0 or (len(pts) == 2 and (ex, ey) == pts[0] and pts[0][0] < pts[1][0]) else -1
                polyline(ctx, [(ex - d * 0.12 * r, ey - 0.11 * r), (ex + d * 0.08 * r, ey), (ex - d * 0.12 * r, ey + 0.11 * r)],
                         5, self.c('pupil', 1, P))
                continue
            if e == 'glow':
                glow(ctx, ex, ey, 0.4 * r, hexc('#e8f0ff'), 0.5)
                ellipse(ctx, ex, ey, 0.13 * r * sx, 0.13 * r, hexc('#f6faff'))
                continue
            er = {'open': 0.135, 'wide': 0.16, 'tiny': 0.16}.get(e, 0.135) * r
            pr = {'open': 0.09, 'wide': 0.075, 'tiny': 0.045}.get(e, 0.09) * r
            ellipse(ctx, ex, ey, er * sx, er, self.c('eye', 1, P))
            circle(ctx, ex + lx * er * 0.35 * sx, ey + ly * er * 0.35, pr, self.c('pupil', 1, P))
        # brows
        by = pts[0][1] - 0.27 * r
        for i, ((ex, ey), sx) in enumerate(zip(pts, sxs)):
            w = 0.14 * r * sx
            if P.brows == 'worried':
                d = 5 if (len(pts) == 2 and i == 0 and pts[0][0] < pts[1][0]) else -5
                a, b = (ex - w, by - d), (ex + w, by + d)
                if pts[0][0] > 0:      # side view: both eyes on the right, inner side is the left
                    a, b = (ex - w, by + 4), (ex + w, by - 5)
            elif P.brows == 'angry':
                a, b = (ex - w, by - 4), (ex + w, by + 4)
            else:
                a, b = (ex - w, by), (ex + w, by)
            line(ctx, a, b, 4.5, self.c('brow', 1, P))

    def _mouth(self, ctx, P, mx, my, wide=1.0):
        r = HR
        m = P.mouth
        mc = self.c('mouth', 1, P)
        if m == 'smile':
            ctx.new_path()
            ctx.arc(mx, my - 0.1 * r, 0.14 * r * wide, 0.2 * math.pi, 0.8 * math.pi)
            ctx.set_line_width(3.5)
            src(ctx, mc)
            ctx.stroke()
        elif m == 'grin':      # the double's wide, wrong smile
            ctx.new_path()
            ctx.arc(mx, my - 0.25 * r, 0.32 * r * wide, 0.12 * math.pi, 0.88 * math.pi)
            ctx.arc_negative(mx, my - 0.3 * r, 0.26 * r * wide, 0.82 * math.pi, 0.18 * math.pi)
            ctx.close_path()
            src(ctx, hexc('#1a0808'))
            ctx.fill()
            for i in range(7):
                a = math.pi * (0.2 + i * 0.1)
                x = mx + math.cos(a) * 0.27 * r * wide
                y = my - 0.27 * r + math.sin(a) * 0.27 * r
                rect(ctx, x - 2.5, y - 4, 5, 6, hexc('#ece6d6'))
        elif m == 'o':
            ellipse(ctx, mx, my, 0.07 * r, 0.1 * r, mc)
        elif m == 'shout':          # wide-open yelling mouth, size from P.mouth_open (0..1)
            o = clamp(P.mouth_open)
            ry = 0.05 * r + 0.2 * r * o
            ellipse(ctx, mx, my + ry * 0.4, 0.2 * r + 0.06 * r * o, ry, hexc('#3a0d0d'))
            if o > 0.25:
                rect(ctx, mx - 0.15 * r, my + ry * 0.4 - ry + 1, 0.3 * r, 0.05 * r, hexc('#f4f0e8'))
                ellipse(ctx, mx, my + ry * 0.4 + ry * 0.55, 0.12 * r, ry * 0.35, hexc('#c94a4a'))
        elif m == 'scream':
            ellipse(ctx, mx, my + 0.03 * r, 0.12 * r, 0.17 * r, mc)
        elif m == 'frown':
            ctx.new_path()
            ctx.arc(mx, my + 0.12 * r, 0.12 * r, 1.2 * math.pi, 1.8 * math.pi)
            ctx.set_line_width(3.5)
            src(ctx, mc)
            ctx.stroke()
        elif m == 'shh':
            line(ctx, (mx - 0.06 * r, my), (mx + 0.06 * r, my), 3.5, mc)
        elif m != 'none':
            line(ctx, (mx - 0.1 * r, my), (mx + 0.1 * r, my), 3.5, mc)

    def _head_side(self, ctx, hc, P):
        r = HR
        hd = P.get('head_down', 0.0)
        ctx.save()
        ctx.translate(*hc)
        ctx.rotate(R(P.head_tilt + 22 * hd))
        circle(ctx, 0, 0, r, self.c('skin_d', 1, P))
        if P.sil is not None:
            circle(ctx, 0.95 * r, 0.1 * r, 0.13 * r, P.sil)
            ctx.restore()
            return
        ctx.save()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.clip()
        circle(ctx, 0.16 * r, -0.12 * r, 0.97 * r, self.c('skin', 1, P))
        self._hair_side(ctx, P, hd)
        ctx.restore()
        circle(ctx, -0.18 * r, 0.12 * r, 0.17 * r, self.c('skin_d', 1, P))           # ear
        circle(ctx, 0.97 * r, 0.12 * r, 0.12 * r, self.c('skin', 0.97, P))           # nose
        if hd < 0.7:
            self._eyes(ctx, P, [(0.46 * r, 0.02 * r + hd * 0.2 * r), (0.78 * r, 0.02 * r + hd * 0.2 * r)], (0.85, 0.7))
            self._mouth(ctx, P, 0.66 * r, 0.47 * r)
        ctx.restore()

    def _side(self, ctx, P):
        t = P.t
        tr = P.tremble
        tx, ty = noise(t * 40, 11) * 2.5 * tr, noise(t * 37, 12) * 2.5 * tr
        hip = (P.hip_dx, -HIP + P.hip_dy)
        lean = R(P.lean)
        ux, uy = math.sin(lean), -math.cos(lean)
        vx, vy = -uy, ux

        def T(v, u):
            return (hip[0] + vx * v + ux * u, hip[1] + vy * v + uy * u)
        out = {}
        hl0 = lean + R(P.head_tilt) * 0.3
        nb0 = T(4, TORSO)
        hc0 = (nb0[0] + math.sin(hl0) * 46 + tx * 0.6, nb0[1] - math.cos(hl0) * 46 + P.head_dy + ty * 0.6)
        sh_b = T(-6, TORSO - 16)
        hand_b = P.hand_b or (6, 150)
        _, hb = self._arm(ctx, sh_b, hand_b, P.bend_b, 0.72, P, tremble=(tx, ty))
        self._leg(ctx, T(-8, 4), P.legs[0], P.legs[1], 0.72, P)
        self._torso_side(ctx, hip, lean, P)
        self._leg(ctx, T(8, 4), P.legs[2], P.legs[3], 1.0, P)
        hl = lean + R(P.head_tilt) * 0.3
        nb = T(4, TORSO)
        hc = (nb[0] + math.sin(hl) * 46 + tx * 0.6, nb[1] - math.cos(hl) * 46 + P.head_dy + ty * 0.6)
        self._head_side(ctx, hc, P)
        out['head'] = hc
        hand_f = P.hand_f or (8, 150)
        sh_f = T(12, TORSO - 16)
        if P.get('finger_lips'):
            hand_f = (hc[0] - sh_f[0] + 66, hc[1] - sh_f[1] + 26)
        if P.get('phone_ear'):          # hand + phone pressed to the ear
            hand_f = (hc[0] - sh_f[0] - 12, hc[1] - sh_f[1] + 22)
        el, hand = self._arm(ctx, sh_f, hand_f, P.bend_f, 1.0, P, front_arm=True, tremble=(tx, ty))
        if P.get('finger_lips'):
            line(ctx, hand, (hand[0] + 4, hand[1] - 34), 9, self.c('skin', 1, P))
        if P.get('phone_ear'):
            ctx.save()
            ctx.translate(hand[0] - 2, hand[1] - 20)
            ctx.rotate(R(-8))
            rrect(ctx, -13, -36, 26, 56, 6, hexc('#0e0f12'))
            if P.get('phone_glow'):
                rrect(ctx, -10, -33, 20, 50, 3, hexc('#7fb8ff'))
            ctx.restore()
            circle(ctx, hand[0], hand[1], HANDR, self.c('skin', 1, P))
        if P.get('phone'):
            ctx.save()
            ctx.translate(*hand)
            ctx.rotate(R(-15))
            rrect(ctx, -10, -30, 24, 46, 5, hexc('#0e0f12'))
            if P.get('phone_glow'):
                rrect(ctx, -7, -27, 18, 40, 3, hexc('#7fb8ff'))
            ctx.restore()
            circle(ctx, hand[0], hand[1], HANDR, self.c('skin', 1, P))
        out['hand'] = hand
        out['hip'] = hip
        return out

    # ------------------------------------------------------------ front / back
    def _torso_front(self, ctx, hip, P, back=False):
        x0 = hip[0]
        rrect(ctx, x0 - 48, hip[1] - TORSO - 4, 96, TORSO + 14, 22, self.c('top', 1, P))
        if P.sil is not None:
            return
        ctx.save()
        rrect_path(ctx, x0 - 48, hip[1] - TORSO - 4, 96, TORSO + 14, 22)
        ctx.clip()
        rect(ctx, x0 - 60, hip[1] - TORSO - 10, 30, TORSO + 30, self.c('top_d', 1, P))
        rect(ctx, x0 - 60, hip[1] - 2, 120, 12, self.c('top_d', 0.95, P))
        if self.st.get('pocket') and not back:
            fill_poly(ctx, [(x0 - 30, hip[1] - 20), (x0 + 30, hip[1] - 20), (x0 + 22, hip[1] - 64),
                            (x0 - 22, hip[1] - 64)], self.c('top_d', 1, P))
        if back and self.st.get('hood'):
            ctx.new_path()
            ctx.move_to(x0 - 42, hip[1] - TORSO - 4)
            ctx.curve_to(x0 - 40, hip[1] - TORSO + 70, x0 + 40, hip[1] - TORSO + 70, x0 + 42, hip[1] - TORSO - 4)
            ctx.close_path()
            src(ctx, self.c('top_d', 1, P))
            ctx.fill()
        ctx.restore()
        if self.st.get('hood') and not back:
            ellipse(ctx, x0, hip[1] - TORSO + 2, 42, 16, self.c('top_d', 1, P))
        if self.st.get('chain') and not back:
            n = 15
            for i in range(n + 1):
                a_ = math.pi * (0.12 + 0.76 * i / n)
                px = x0 + math.cos(a_) * 40
                py = hip[1] - TORSO + 8 + math.sin(a_) * 58
                ctx.new_path()
                ctx.arc(px, py, 5.2, 0, 2 * math.pi)
                ctx.set_line_width(3.4)
                src(ctx, mul(hexc('#d9dde4'), P.lit))
                ctx.stroke()
            ctx.new_path()
            ctx.move_to(x0, hip[1] - TORSO + 66)
            ctx.line_to(x0 + 13, hip[1] - TORSO + 82)
            ctx.line_to(x0, hip[1] - TORSO + 100)
            ctx.line_to(x0 - 13, hip[1] - TORSO + 82)
            ctx.close_path()
            src(ctx, mul(hexc('#e8ecf2'), P.lit))
            ctx.fill()
            circle(ctx, x0 - 4, hip[1] - TORSO + 78, 3, (1, 1, 1, 0.9))
            for sx in (-1, 1):
                line(ctx, (x0 + sx * 12, hip[1] - TORSO + 12), (x0 + sx * 14, hip[1] - TORSO + 56), 3,
                     mul(hexc('#eef2f8'), P.lit))

    def _legs_front(self, ctx, hip, P):
        sit = P.get('sit')
        for sx in (-1, 1):
            k = 0.9 if sx < 0 else 1.0
            pc = self.c('pants', k, P)
            h = (hip[0] + sx * 22, hip[1] + 2)
            if sit:
                kn = (hip[0] + sx * 30, hip[1] + 26)
                ft = (hip[0] + sx * 34, -10)
                taper(ctx, kn, ft, LEGW + 2, LEGW + 4, pc)
                rrect(ctx, kn[0] - LEGW * 0.7, hip[1] - 6, LEGW * 1.4, kn[1] - hip[1] + 16, 16, mul(pc, 1.25))
                ellipse(ctx, kn[0], kn[1] + 4, LEGW * 0.72, 14, mul(pc, 1.6))   # knee coming towards us
            else:
                ft = (hip[0] + sx * 26, -10)
                taper(ctx, h, ft, LEGW + 2, LEGW + 4, pc)
            ellipse(ctx, ft[0] + sx * 6, ft[1] + 4, 26, 12, self.c('shoe', 1, P))

    def _head_front(self, ctx, hc, P, back=False):
        r = HR
        hd = P.get('head_down', 0.0)
        ctx.save()
        ctx.translate(*hc)
        ctx.rotate(R(P.head_tilt))
        for sx in (-1, 1):
            circle(ctx, sx * 0.97 * r, 0.1 * r + hd * 0.1 * r, 0.17 * r, self.c('skin_d', 1, P))
        circle(ctx, 0, 0, r, self.c('skin_d', 1, P))
        if P.sil is not None:
            ctx.restore()
            return
        ctx.save()
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.clip()
        circle(ctx, 0.1 * r, -0.1 * r, 0.97 * r, self.c('skin', 1, P))
        hair = self.c('hair', 1, P)
        if hair is not None:
            if back:
                circle(ctx, 0, 0, r, hair)
                rect(ctx, -r, 0.55 * r, 2 * r, r, self.c('skin_d', 1, P))
            else:
                y0 = -0.22 * r + hd * 0.42 * r
                pts = [(-1.2 * r, 0.25 * r), (-1.2 * r, -1.2 * r), (1.2 * r, -1.2 * r), (1.2 * r, 0.25 * r),
                       (0.86 * r, 0.2 * r), (0.8 * r, y0)]
                for i in range(7):
                    x = 0.72 * r - i * 0.24 * r
                    pts.append((x, y0 + (0.1 * r if i % 2 == 0 else -0.02 * r)))
                pts += [(-0.8 * r, y0), (-0.86 * r, 0.2 * r)]
                fill_poly(ctx, pts, hair)
            ctx.save()
            ctx.arc(0, 0, r, 0, 2 * math.pi)
            ctx.clip()
            fill_poly(ctx, [(-1.2 * r, -1.2 * r), (-0.4 * r, -1.2 * r), (-0.9 * r, 0.3 * r), (-1.2 * r, 0.3 * r)],
                      self.c('hair_d', 1, P))
            ctx.restore()
        ctx.restore()
        if self.st.get('cap') is not None and not back:
            cc = self.c('cap', 1, P)
            ctx.save()
            ctx.new_path()
            ctx.arc(0, -0.16 * r, 1.03 * r, math.pi * 1.0, math.pi * 2.0)
            ctx.line_to(1.03 * r, -0.26 * r)
            ctx.line_to(-1.03 * r, -0.26 * r)
            ctx.close_path()
            src(ctx, cc)
            ctx.fill()
            ellipse(ctx, -0.35 * r, -0.62 * r, 0.32 * r, 0.22 * r, mul(cc, 1.25))          # highlight
            circle(ctx, 0, -1.08 * r, 0.09 * r, mul(cc, 0.8))                              # button
            # baseball-cap brim pointing at the viewer (seen from below: a darker crescent)
            ctx.new_path()
            ctx.move_to(-0.95 * r, -0.24 * r)
            ctx.curve_to(-0.6 * r, -0.36 * r, 0.6 * r, -0.36 * r, 0.95 * r, -0.24 * r)
            ctx.curve_to(0.85 * r, 0.02 * r, -0.85 * r, 0.02 * r, -0.95 * r, -0.24 * r)
            ctx.close_path()
            src(ctx, mul(cc, 0.82))
            ctx.fill()
            ctx.new_path()
            ctx.move_to(-0.88 * r, -0.14 * r)
            ctx.curve_to(-0.5 * r, -0.02 * r, 0.5 * r, -0.02 * r, 0.88 * r, -0.14 * r)
            ctx.set_line_width(3)
            src(ctx, mul(cc, 0.5))
            ctx.stroke()
            if self.st.get('cap_logo'):
                circle(ctx, 0, -0.56 * r, 0.17 * r, self.st['cap_logo'])
                circle(ctx, 0, -0.56 * r, 0.09 * r, cc)
            ctx.restore()
        if not back:
            if hd < 0.6:
                ey = 0.02 * r + hd * 0.3 * r
                self._eyes(ctx, P, [(-0.32 * r, ey), (0.32 * r, ey)])
                ellipse(ctx, 0, 0.2 * r + hd * 0.2 * r, 0.08 * r, 0.06 * r, self.c('skin_d', 0.95, P))
                self._mouth(ctx, P, 0, 0.45 * r + hd * 0.25 * r, wide=1.0)
            else:
                ellipse(ctx, 0, 0.55 * r, 0.1 * r, 0.06 * r, self.c('skin_d', 0.9, P))
        ctx.restore()

    def _front(self, ctx, P, back=False):
        t = P.t
        tr = P.tremble
        tx, ty = noise(t * 40, 11) * 2.5 * tr, noise(t * 37, 12) * 2.5 * tr
        seat = P.get('sit')
        hip = (P.hip_dx, (-seat if seat else -HIP) + P.hip_dy)
        out = {}
        self._legs_front(ctx, hip, P)
        if back:
            for sx in (-1, 1):
                self._arm(ctx, (hip[0] + sx * 44, hip[1] - TORSO + 14), (sx * 14, 150), sx, 1.0, P)
        self._torso_front(ctx, hip, P, back)
        hd = P.get('head_down', 0.0)
        hc = (hip[0] + tx * 0.6, hip[1] - TORSO - 46 + 14 * hd + P.head_dy + ty * 0.6)
        self._head_front(ctx, hc, P, back)
        out['head'] = hc
        if not back:
            for sx, hand, k in ((-1, P.hand_b, 0.92), (1, P.hand_f, 1.0)):
                shp = (hip[0] + sx * 44, hip[1] - TORSO + 14)
                if hand is None:
                    hand = (sx * 14, 150) if not seat else (sx * -12, 158)
                else:
                    hand = (hand[0] * sx, hand[1])
                if sx > 0 and P.get('finger_lips'):
                    hand = (hc[0] - shp[0] + 2, hc[1] - shp[1] + 40)
                bend = sx
                if P.get('ears'):             # palms pressed over the ears, elbows out
                    hand = (hc[0] + sx * 0.98 * HR - shp[0], hc[1] - shp[1] + 6)
                    bend = -sx
                el, tg = self._arm(ctx, shp, hand, bend, k, P, front_arm=(sx > 0), tremble=(tx, ty))
                if sx > 0 and P.get('finger_lips'):
                    line(ctx, tg, (tg[0], tg[1] - 34), 9, self.c('skin', 1, P))
                out['hand_r' if sx > 0 else 'hand_l'] = tg
        return out

    def _back(self, ctx, P):
        return self._front(ctx, P, back=True)


HERO = Toon(HERO3)
DOUBLE = Toon(HERO3)
PASS = [Toon(s) for s in PASSENGERS]
