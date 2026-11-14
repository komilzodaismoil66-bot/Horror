"""«Крик»: prehistoric field, jungle, mountains, sea, birds, dinosaurs, space, planets, galaxy."""
import math
import random
import cairo
from engine import *

GROUND = 1180          # top of the field
HORIZON = 1010


def smooth_path(ctx, pts, closed=True):
    """Catmull-Rom spline through pts as a cairo path."""
    n = len(pts)
    ctx.new_path()
    ctx.move_to(*pts[0])
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        ctx.curve_to(*c1, *c2, *p2)
    if closed:
        ctx.close_path()


def fill_smooth(ctx, pts, c):
    smooth_path(ctx, pts)
    src(ctx, c)
    ctx.fill()


# ---------------------------------------------------------------- sky
def sky(ctx, t, heat=0.0, x0=-600, w=2400):
    top = mix(hexc('#3d8fe0'), hexc('#5a1408'), heat)
    low = mix(hexc('#bfe4ff'), hexc('#ff7a1a'), heat)
    vgrad(ctx, x0, -800, w, HORIZON + 900, [(0, top), (1, low)])
    sx, sy = 880, 330
    glow(ctx, sx, sy, 260 + 500 * heat, mix(hexc('#fff6c0'), hexc('#ffb040'), heat), 0.55 + 0.4 * heat)
    circle(ctx, sx, sy, 62 + 60 * heat, mix(hexc('#fffbe0'), hexc('#ffd27a'), heat))


CLOUDS = [(-100, 700, 1.0), (380, 610, 1.3), (760, 760, 0.9), (1100, 640, 1.1), (180, 860, 0.7)]


def clouds(ctx, t, heat=0.0, blow=0.0):
    for i, (x, y, s) in enumerate(CLOUDS):
        xx = (x + t * 12 * s + blow * 900 * (1 if i % 2 else -1)) % 1700 - 300
        a = 1 - heat
        if a <= 0:
            continue
        c = alpha(mix(hexc('#ffffff'), hexc('#ffb080'), heat), a)
        for dx, dy, r in ((0, 0, 60), (55, -25, 70), (115, 0, 58), (60, 15, 60), (-45, 10, 45)):
            circle(ctx, xx + dx * s, y + dy * s, r * s, c)


# ---------------------------------------------------------------- mountains
MOUNTS = [(-140, 470, 430), (210, 360, 480), (500, 520, 360)]   # (x, peak_y, half_width)


def mountains(ctx, t, collapse=0.0, heat=0.0):
    r = random.Random(4)
    for i, (x, py, hw) in enumerate(MOUNTS):
        c = mix(hexc('#7d8fb0'), hexc('#5a2a20'), heat)
        dark = mul(c, 0.78)
        k = ease_in(clamp(collapse * 1.4 - i * 0.2))
        top = py + (HORIZON - py) * 0.62 * k
        jag = []
        n = 9
        for j in range(n + 1):
            f = j / n
            xx = x - hw + 2 * hw * f
            h = 1 - abs(f - 0.5) * 2
            yy = HORIZON - (HORIZON - top) * h ** 0.9
            yy += r.uniform(-18, 18) * (1 + 6 * k) * (0.3 + h)
            jag.append((xx, yy))
        pts = [(x - hw, HORIZON + 10)] + jag + [(x + hw, HORIZON + 10)]
        fill_poly(ctx, pts, c)
        fill_poly(ctx, [(x, top + 6)] + [p for p in jag if p[0] >= x] + [(x + hw, HORIZON + 10), (x, HORIZON + 10)], dark)
        if k < 0.6 and heat < 0.5:
            sc = [(x - hw * 0.28, top + (HORIZON - top) * 0.28), (x, top - 4), (x + hw * 0.26, top + (HORIZON - top) * 0.3),
                  (x + hw * 0.1, top + (HORIZON - top) * 0.22), (x - hw * 0.05, top + (HORIZON - top) * 0.33)]
            fill_poly(ctx, sc, alpha(hexc('#f4f8ff'), 1 - k / 0.6))
    # rock slides + dust
    if collapse > 0:
        rr = random.Random(9)
        for i in range(60):
            st = rr.uniform(0, 0.7)
            lt = collapse - st
            if lt < 0:
                continue
            m = MOUNTS[i % 3]
            x0 = m[0] + rr.uniform(-0.5, 0.5) * m[2] * 0.6
            y0 = m[1] + rr.uniform(0, 120)
            x = x0 + (rr.random() - 0.5) * 300 * lt
            y = min(HORIZON, y0 + 900 * lt * lt + 200 * lt)
            s = rr.uniform(12, 40)
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(lt * rr.uniform(-6, 6))
            fill_poly(ctx, [(-s, -s * 0.4), (s * 0.3, -s), (s, s * 0.2), (-s * 0.2, s * 0.7)], hexc('#5a6278'))
            ctx.restore()
        for i in range(14):
            x = MOUNTS[i % 3][0] + rr.uniform(-200, 200)
            rad = 120 + 380 * collapse * rr.uniform(0.6, 1.2)
            radial(ctx, x, HORIZON - 120 - 260 * collapse * rr.random(), rad, hexc('#a89a88'), 0.55 * min(1, collapse * 2))


def sea(ctx, t, evap=0.0, heat=0.0):
    x0, x1 = 560, 1700
    y0 = HORIZON - 6
    rect(ctx, x0, y0, x1 - x0, 80, mix(hexc('#cdb88e'), hexc('#6a3a24'), heat))      # sea bed
    level = 1 - evap
    if level > 0.02:
        h = 70 * level
        rect(ctx, x0 + 120 * evap, y0 + (70 - h), x1 - x0, h + 10, mix(hexc('#2e7fc8'), hexc('#b0603a'), heat * 0.6))
        for i in range(8):
            xx = x0 + 160 + i * 130 + math.sin(t * 2 + i) * 20
            line(ctx, (xx, y0 + 80 - h + 10), (xx + 50, y0 + 80 - h + 10), 3, (1, 1, 1, 0.5 * level))
    if evap > 0:
        rr = random.Random(5)
        for i in range(26):
            ph = (t * 0.35 + rr.random()) % 1
            x = rr.uniform(x0 + 40, 1300)
            y = y0 + 40 - ph * 700
            radial(ctx, x + ph * 60, y, 70 + 160 * ph, hexc('#f2f2f2'), 0.6 * (1 - ph) * min(1, evap * 3))


# ---------------------------------------------------------------- jungle
def _palm(ctx, x, y, h, ang, c, leaf, t, rustle):
    top = (x + math.sin(ang) * h, y - math.cos(ang) * h)
    taper(ctx, (x, y), top, 26, 16, c)
    for k in range(7):
        a = -math.pi / 2 + (k - 3) * 0.48 + ang + math.sin(t * 9 + k + x) * 0.18 * rustle
        L = 110
        tip = (top[0] + math.cos(a) * L, top[1] + math.sin(a) * L * 0.6 + 40)
        mid = ((top[0] + tip[0]) / 2, (top[1] + tip[1]) / 2 - 30)
        ctx.new_path()
        ctx.move_to(*top)
        ctx.curve_to(mid[0], mid[1] - 20, tip[0], tip[1] - 10, *tip)
        ctx.curve_to(tip[0] - 10, tip[1] + 12, mid[0], mid[1] + 24, *top)
        src(ctx, leaf)
        ctx.fill()


def _canopy(ctx, x, y, h, ang, trunk, leaf, leaf_d, t, rustle, seed):
    top = (x + math.sin(ang) * h, y - math.cos(ang) * h)
    taper(ctx, (x, y), top, 40, 24, trunk)
    r = random.Random(seed)
    for k in range(7):
        dx = r.uniform(-120, 120)
        dy = r.uniform(-90, 40)
        jx = math.sin(t * 11 + k * 2 + seed) * 6 * rustle
        jy = math.cos(t * 13 + k + seed) * 4 * rustle
        circle(ctx, top[0] + dx * 0.7 + jx, top[1] + dy * 0.6 + jy, r.uniform(44, 70), leaf_d if k % 3 == 0 else leaf)


def _fern(ctx, x, y, s, ang, c, t, rustle):
    for k in range(6):
        a = -math.pi / 2 + (k - 2.5) * 0.4 + ang + math.sin(t * 10 + k + x) * 0.15 * rustle
        tip = (x + math.cos(a) * 110 * s, y + math.sin(a) * 110 * s)
        taper(ctx, (x, y), tip, 18 * s, 2, c, round_ends=False)


R_J = random.Random(21)
TREES = sorted([(R_J.uniform(-200, 1300), R_J.choice(['palm', 'canopy', 'canopy', 'palm', 'tall']),
                 R_J.uniform(0.8, 1.25), R_J.randint(0, 999)) for _ in range(26)], key=lambda q: q[2])
FERNS = [(R_J.uniform(-100, 1200), R_J.uniform(0.8, 1.4)) for _ in range(22)]


def jungle(ctx, t, rustle=0.0, shake=0.0, flatten=0.0, burn=0.0, hero_x=540):
    base = GROUND + 30
    rect(ctx, -400, HORIZON + 40, 2000, base - HORIZON, mix(hexc('#1f5a2c'), hexc('#1a0e08'), burn))
    for (x, kind, s, seed) in TREES:
        y = base - 20 + (s - 1) * 60
        side = 1 if x > hero_x else -1
        ang = noise(t * 2 + seed, seed) * 0.03 * (1 + rustle) + shake * 0.14 * math.sin(t * 17 + seed) + \
            flatten * side * 0.9 * clamp(1 - abs(x - hero_x) / 1600 + 0.3)
        trunk = mix(hexc('#5a3c22'), hexc('#120806'), burn)
        leaf = mix(hexc('#2f8a3a') if s > 1.05 else hexc('#246f30'), hexc('#1a0b06'), burn)
        leaf_d = mul(leaf, 0.75)
        if kind == 'palm':
            _palm(ctx, x, y, 175 * s, ang, trunk, leaf, t, rustle + shake * 3)
        elif kind == 'tall':
            _canopy(ctx, x, y, 230 * s, ang, trunk, leaf_d, leaf, t, rustle + shake * 3, seed)
        else:
            _canopy(ctx, x, y, 150 * s, ang, trunk, leaf, leaf_d, t, rustle + shake * 3, seed)
        if burn > 0.3:
            from envs import flame
            if seed % 3 == 0:
                top = (x + math.sin(ang) * 160 * s, y - math.cos(ang) * 160 * s)
                flame(ctx, top[0], top[1] + 40, 120, 160 * burn, t, seed % 50, a=min(1, burn * 1.5))
    for (x, s) in FERNS:
        side = 1 if x > hero_x else -1
        _fern(ctx, x, base + 30, s, flatten * side * 0.8 + shake * 0.2 * math.sin(t * 19 + x), mix(hexc('#3a9a42'),
              hexc('#1a0b06'), burn), t, rustle + shake * 3)


def falling_leaves(ctx, t, amount, seed=3):
    if amount <= 0:
        return
    r = random.Random(seed)
    for i in range(int(50 * amount)):
        ph = (t * r.uniform(0.15, 0.35) + r.random()) % 1
        x = r.uniform(-100, 1180) + math.sin(t * 2 + i) * 40 + ph * 120
        y = 820 + ph * 700
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(t * 3 + i)
        ellipse(ctx, 0, 0, 10, 5, alpha(hexc('#3c9a3a'), 1 - ph * 0.5))
        ctx.restore()


# ---------------------------------------------------------------- field
R_G = random.Random(8)
TUFTS = [(R_G.uniform(-100, 1180), R_G.uniform(GROUND + 40, 1950)) for _ in range(150)]


def crack_tree(seed=2):
    """Jagged ground cracks radiating from the hero's feet: list of (pts, start_fraction, width)."""
    r = random.Random(seed)
    out = []

    def grow(p, ang, L, depth, f0, w):
        pts = [p]
        x, y = p
        steps = int(L / 55)
        for i in range(steps):
            ang += r.uniform(-0.7, 0.7) * 0.6
            x += math.cos(ang) * 55
            y += math.sin(ang) * 55 * 0.45
            pts.append((x, y))
            if depth < 1 and r.random() < 0.18:
                grow((x, y), ang + r.choice([-1, 1]) * r.uniform(0.6, 1.1), L * 0.35, depth + 1,
                     f0 + 0.6 * i / steps, w * 0.5)
        out.append((pts, f0, w))
    for k in range(7):
        grow((540, 1740), -math.pi + k * (2 * math.pi / 7) + r.uniform(-0.25, 0.25), 1000, 0, 0.0, 22)
    return out


CRACKS = crack_tree()


def field(ctx, t, sway=0.0, cracks=0.0, heat=0.0, lava=0.0):
    g0 = mix(hexc('#7cc04a'), hexc('#5a2a14'), heat)
    g1 = mix(hexc('#5aa236'), hexc('#2a1008'), heat)
    vgrad(ctx, -600, GROUND, 2400, 1200, [(0, g1), (0.25, g0), (1, mul(g0, 0.85))])
    for (x, y) in TUFTS:
        s = 0.6 + (y - GROUND) / 900
        bend = math.sin(t * 3 + x * 0.05) * 0.15 + sway * math.sin(t * 9 + x * 0.1) * 0.5
        c = mix(hexc('#4e9a2c'), hexc('#2a1208'), heat)
        for k in (-1, 0, 1):
            a = -math.pi / 2 + k * 0.35 + bend
            line(ctx, (x + k * 4 * s, y), (x + math.cos(a) * 26 * s, y + math.sin(a) * 26 * s), 4 * s, c)
    if cracks > 0:
        for pts, f0, w0 in CRACKS:
            f = clamp((cracks - f0) / (1 - f0 + 1e-6))
            if f <= 0:
                continue
            n = max(2, int(len(pts) * f))
            for i in range(n - 1):
                w = w0 * (1 - i / len(pts)) + 2
                a_, b_ = pts[i], pts[i + 1]
                if lava > 0:
                    line(ctx, a_, b_, w + 14, alpha(hexc('#ff6a10'), 0.4 * lava), cairo.LINE_CAP_ROUND)
                line(ctx, (a_[0], a_[1] - 3), (b_[0], b_[1] - 3), w + 4, mix(hexc('#6f8a3a'), hexc('#ff9a30'), lava),
                     cairo.LINE_CAP_ROUND)
                line(ctx, a_, b_, w, mix(hexc('#120d0a'), hexc('#ffd050'), lava), cairo.LINE_CAP_ROUND)
    shadow_y = 1735
    ellipse(ctx, 540, shadow_y, 150, 24, (0, 0, 0, 0.22))


# ---------------------------------------------------------------- birds
R_B = random.Random(31)
BIRDS = [(R_B.uniform(0, 1080), R_B.uniform(880, 1100), R_B.uniform(-1, 1), R_B.uniform(0.7, 1.3), R_B.random())
         for _ in range(34)]


def birds(ctx, t, lt):
    """lt = seconds since the flock was scared off."""
    if lt < 0:
        return
    for (x, y, dx, s, ph) in BIRDS:
        tt_ = max(0, lt - ph * 0.6)
        if tt_ <= 0:
            continue
        bx = x + dx * 260 * tt_ + (1 if dx > 0 else -1) * 60 * tt_ * tt_
        by = y - 260 * tt_ - 40 * tt_ * tt_
        flap = math.sin(t * 24 + ph * 10)
        w = 26 * s
        c = hexc('#22252c')
        polyline(ctx, [(bx - w, by - flap * 12 * s), (bx - w * 0.3, by - 4), (bx, by), (bx + w * 0.3, by - 4),
                       (bx + w, by - flap * 12 * s)], 5 * s, c)


# ---------------------------------------------------------------- dinosaurs
def _leg(ctx, hip, a, l1, l2, l3, w, c, lift=0.0):
    knee = (hip[0] + math.sin(a) * l1, hip[1] + math.cos(a) * l1)
    b = a - 1.0
    ankle = (knee[0] + math.sin(b) * l2, knee[1] + math.cos(b) * l2 - lift)
    cc = a + 0.55
    toe = (ankle[0] + math.sin(cc) * l3, ankle[1] + math.cos(cc) * l3)
    taper(ctx, hip, knee, w, w * 0.62, c)
    taper(ctx, knee, ankle, w * 0.58, w * 0.36, c)
    taper(ctx, ankle, toe, w * 0.34, w * 0.24, c)
    for k in (-0.3, 0.0, 0.3):
        d = cc + 0.9 + k
        tp = (toe[0] + math.sin(d) * w * 0.45, toe[1] + math.cos(d) * w * 0.2 + 3)
        taper(ctx, toe, tp, w * 0.16, 2, mul(c, 0.7), round_ends=False)
    return toe


def trex(ctx, x, y, s, t, run=1.0, jaw=0.3, facing=1):
    body = hexc('#5f5a38')
    belly = hexc('#a19866')
    dark = hexc('#3f3c24')
    ph = t * 2.2 * run
    bob = -abs(math.sin(ph * math.pi * 2)) * 10 * run
    ctx.save()
    ctx.translate(x, y + bob * s)
    ctx.scale(s * facing, s)
    hip = (-40, -175)
    a = math.sin(ph * 2 * math.pi) * 0.55 * run
    _leg(ctx, (hip[0] - 10, hip[1]), -a, 130, 120, 70, 66, mul(body, 0.7), lift=max(0, math.cos(ph * 2 * math.pi)) * 30)
    pts = [(-470, -182), (-330, -208), (-180, -240), (-40, -265), (70, -260), (150, -238), (205, -255), (232, -296),
           (300, -304), (370, -290), (394, -266), (388, -244), (300, -238), (252, -214), (224, -176), (170, -140),
           (60, -110), (-40, -122), (-160, -160), (-320, -180)]
    fill_smooth(ctx, pts, body)
    ctx.save()
    smooth_path(ctx, pts)
    ctx.clip()
    ellipse(ctx, 40, -100, 230, 60, belly)
    for i in range(9):
        xx = -340 + i * 50
        fill_poly(ctx, [(xx, -330), (xx + 22, -330), (xx + 12, -222 - 5 * math.sin(i)), (xx - 8, -222)], dark)
    ctx.restore()
    # lower jaw
    ja = 0.12 + 0.35 * jaw
    hinge = (252, -232)
    jp = [(252, -232), (380, -244), (374, -228), (300, -214), (254, -208)]
    jp = [rot(p, ja, hinge) for p in jp]
    fill_smooth(ctx, jp, mul(body, 0.9))
    for i in range(7):
        f = i / 6
        p = (262 + 112 * f, -238 - 4 * f)
        fill_poly(ctx, [(p[0] - 5, p[1]), (p[0], p[1] + 12), (p[0] + 5, p[1])], hexc('#f2ecd8'))
        q = rot((262 + 108 * f, -214 - 2 * f), ja, hinge)
        fill_poly(ctx, [(q[0] - 4, q[1]), (q[0], q[1] - 9), (q[0] + 4, q[1])], hexc('#f2ecd8'))
    circle(ctx, 302, -276, 10, hexc('#e8c040'))
    ellipse(ctx, 303, -276, 3, 8, hexc('#111111'))
    line(ctx, (284, -292), (322, -286), 6, dark)
    circle(ctx, 372, -270, 4, hexc('#1a1a10'))
    # tiny arms
    taper(ctx, (190, -168), (214, -138), 16, 12, mul(body, 0.85))
    taper(ctx, (214, -138), (236, -150), 12, 8, mul(body, 0.85))
    for k in (0, 1):
        line(ctx, (236, -150), (246, -156 + k * 10), 3, hexc('#e8e0c8'))
    _leg(ctx, hip, a, 130, 120, 70, 72, body, lift=max(0, -math.cos(ph * 2 * math.pi)) * 30)
    ctx.restore()


def triceratops(ctx, x, y, s, t, run=1.0, facing=1, seed=0):
    body = hexc('#7d6a46')
    belly = hexc('#ab9a6c')
    frill = hexc('#a2582e')
    ph = t * 2.6 * run + seed * 0.3
    bob = -abs(math.sin(ph * math.pi * 2)) * 6 * run
    ctx.save()
    ctx.translate(x, y + bob * s)
    ctx.scale(s * facing, s)

    def leg(px, py, ang, c, L=110, w=52):
        knee = (px + math.sin(ang) * L * 0.5, py + L * 0.5)
        foot = (knee[0] + math.sin(ang * 0.6) * L * 0.5, py + L)
        taper(ctx, (px, py), knee, w, w * 0.8, c)
        taper(ctx, knee, foot, w * 0.8, w * 0.75, c)
        ellipse(ctx, foot[0] + 6, foot[1] - 4, w * 0.5, 10, mul(c, 0.8))
    a = math.sin(ph * 2 * math.pi) * 0.5 * run
    leg(-160, -110, -a, mul(body, 0.7))
    leg(170, -100, a, mul(body, 0.7), 100)
    # frill with spikes
    ctx.save()
    ctx.translate(238, -196)
    ctx.rotate(-0.45)
    for k in range(11):
        an = math.pi * 0.62 + k * math.pi * 0.08
        p = (math.cos(an) * 98, math.sin(an) * 122)
        q = (math.cos(an) * 128, math.sin(an) * 152)
        taper(ctx, p, q, 22, 2, mul(frill, 0.8), round_ends=False)
    ellipse(ctx, 0, 0, 100, 126, frill)
    for k in range(5):
        circle(ctx, -40 + k * 20, -60 + k * 30, 9, hexc('#6a3416'))
    ctx.restore()
    pts = [(-390, -118), (-270, -168), (-120, -222), (40, -236), (150, -212), (210, -184), (240, -150), (248, -112),
           (200, -88), (100, -78), (-60, -84), (-200, -94), (-300, -104)]
    fill_smooth(ctx, pts, body)
    ctx.save()
    smooth_path(ctx, pts)
    ctx.clip()
    ellipse(ctx, 0, -70, 260, 50, belly)
    for i in range(6):
        circle(ctx, -200 + i * 60, -190 + 10 * math.sin(i), 10, mul(body, 0.8))
    ctx.restore()
    face = [(234, -172), (300, -160), (360, -134), (394, -100), (380, -84), (330, -86), (270, -100), (236, -126)]
    fill_smooth(ctx, face, mul(body, 1.05))
    fill_poly(ctx, [(370, -116), (404, -96), (386, -82)], hexc('#3a2e20'))       # beak
    taper(ctx, (300, -162), (406, -236), 20, 3, hexc('#e8dcc0'), round_ends=False)
    taper(ctx, (282, -166), (380, -246), 16, 3, hexc('#c8bca0'), round_ends=False)
    taper(ctx, (362, -126), (384, -160), 14, 3, hexc('#e8dcc0'), round_ends=False)
    circle(ctx, 304, -140, 6, hexc('#111111'))
    circle(ctx, 306, -142, 2, (1, 1, 1, 1))
    leg(-130, -110, a, body)
    leg(190, -100, -a, body, 100)
    ctx.restore()


def raptor(ctx, x, y, s, t, facing=1, seed=0):
    body = hexc('#6f5c3a')
    dark = hexc('#3e3120')
    ph = t * 3.6 + seed * 0.37
    ctx.save()
    ctx.translate(x, y - abs(math.sin(ph * math.pi * 2)) * 8 * s)
    ctx.scale(s * facing, s)
    a = math.sin(ph * 2 * math.pi) * 0.7
    _leg(ctx, (-10, -90), -a, 60, 58, 34, 30, mul(body, 0.7), lift=max(0, math.cos(ph * 2 * math.pi)) * 20)
    pts = [(-230, -112), (-100, -122), (0, -128), (70, -140), (110, -170), (165, -178), (190, -166), (186, -152),
           (132, -150), (100, -128), (60, -96), (-10, -82), (-90, -94)]
    fill_smooth(ctx, pts, body)
    for i in range(6):
        xx = -160 + i * 36
        line(ctx, (xx, -122), (xx + 10, -100), 7, dark)
    circle(ctx, 160, -164, 4, hexc('#111111'))
    line(ctx, (150, -152), (188, -156), 2, hexc('#2a2014'))
    taper(ctx, (70, -128), (96, -104), 10, 7, mul(body, 0.85))
    for k in range(4):
        line(ctx, (40 + k * 10, -132), (52 + k * 12, -112), 3, mul(body, 0.6))     # arm feathers
    _leg(ctx, (0, -90), a, 60, 58, 34, 32, body, lift=max(0, -math.cos(ph * 2 * math.pi)) * 20)
    ctx.restore()


def sauropod(ctx, x, y, s, t, facing=1):
    body = hexc('#69705e')
    ph = t * 1.2
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s * facing, s)
    neck_sw = math.sin(ph) * 0.08
    for (lx, k) in ((-150, 0.7), (180, 0.7)):
        a = math.sin(ph * 2 * math.pi + (0 if lx < 0 else 3)) * 0.2
        taper(ctx, (lx, -260), (lx + math.sin(a) * 60, 0), 90, 80, mul(body, k))
    fill_smooth(ctx, [(-620, -200), (-400, -260), (-200, -360), (60, -400), (240, -380), (300, -300), (200, -200),
                      (-100, -180), (-400, -200)], body)
    ctx.new_path()
    ctx.move_to(200, -380)
    nx, ny = 460 + neck_sw * 600, -1000
    ctx.curve_to(300, -520, 380 + neck_sw * 300, -800, nx, ny)
    ctx.line_to(nx + 60, ny + 30)
    ctx.curve_to(420 + neck_sw * 300, -760, 360, -480, 300, -300)
    ctx.close_path()
    src(ctx, body)
    ctx.fill()
    fill_smooth(ctx, [(nx - 20, ny - 10), (nx + 30, ny - 50), (nx + 110, ny - 20), (nx + 110, ny + 10),
                      (nx + 40, ny + 30)], body)
    circle(ctx, nx + 52, ny - 22, 6, hexc('#111111'))
    for (lx, k) in ((-110, 1.0), (220, 1.0)):
        a = math.sin(ph * 2 * math.pi + (3 if lx < 0 else 0)) * 0.2
        taper(ctx, (lx, -250), (lx + math.sin(a) * 60, 0), 92, 82, body)
    ctx.restore()


def pterosaur(ctx, x, y, s, t, facing=1, seed=0):
    c = hexc('#8a5c3a')
    w = hexc('#a8704a')
    fl = math.sin(t * 9 + seed)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s * facing, s)
    tip_y = -60 * fl
    fill_poly(ctx, [(-10, -6), (-170, tip_y - 10), (-120, tip_y + 30), (-20, 16)], w)
    fill_poly(ctx, [(10, -6), (170, tip_y - 10), (120, tip_y + 30), (20, 16)], mul(w, 0.85))
    ellipse(ctx, 0, 0, 40, 16, c)
    fill_poly(ctx, [(30, -10), (120, 4), (34, 8)], c)                      # beak
    fill_poly(ctx, [(28, -10), (-30, -40), (10, -14)], c)                  # crest
    circle(ctx, 38, -4, 3, hexc('#111111'))
    ctx.restore()


# ---------------------------------------------------------------- space
R_S = random.Random(77)
STARS = [(R_S.uniform(-300, 1400), R_S.uniform(-300, 2200), R_S.uniform(0.8, 2.6), R_S.random()) for _ in range(420)]


def space_bg(ctx, t, streak=0.0, cx=540, cy=900):
    rect(ctx, -2000, -2000, 6000, 6000, hexc('#04040c'))
    glow(ctx, 300, 600, 900, hexc('#3a1a6a'), 0.35)
    glow(ctx, 900, 1400, 900, hexc('#0a3a6a'), 0.3)
    for (x, y, r, ph) in STARS:
        a = 0.5 + 0.5 * math.sin(t * 3 + ph * 20)
        if streak > 0:
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy) or 1
            L = streak * 120 * (d / 900)
            line(ctx, (x, y), (x + dx / d * L, y + dy / d * L), r, (1, 1, 1, 0.7 * a))
        else:
            circle(ctx, x, y, r, (1, 1, 1, 0.8 * a))


CONT = [[(-0.5, -0.4), (-0.1, -0.6), (0.2, -0.3), (0.0, 0.0), (-0.4, 0.1)],
        [(0.3, 0.1), (0.6, -0.1), (0.7, 0.3), (0.4, 0.6), (0.2, 0.4)],
        [(-0.6, 0.3), (-0.3, 0.4), (-0.35, 0.7), (-0.65, 0.55)]]


def earth(ctx, x, y, r, t, heat=1.0, crack=0.0, split=0.0):
    glow(ctx, x, y, r * 1.5, mix(hexc('#6ab8ff'), hexc('#ff6a20'), heat), 0.45)
    pieces = 8

    def body():
        circle(ctx, x, y, r, mix(hexc('#2a6fc0'), hexc('#a8301a'), heat))
        for cpts in CONT:
            fill_smooth(ctx, [(x + px * r, y + py * r) for px, py in cpts], mix(hexc('#3c9a44'), hexc('#3a120a'), heat))
        rr = random.Random(3)
        for i in range(14):
            a = rr.uniform(0, 2 * math.pi)
            d = rr.uniform(0.2, 0.9) * r
            radial(ctx, x + math.cos(a) * d, y + math.sin(a) * d, r * 0.25, hexc('#ffb040'), 0.35 * heat)
        if crack > 0:
            rr = random.Random(8)
            for k in range(pieces):
                a = 2 * math.pi * k / pieces + 0.2
                pts = [(x, y)]
                for j in range(1, 7):
                    d = r * j / 6 * clamp(crack * 1.4)
                    aa = a + rr.uniform(-0.12, 0.12)
                    pts.append((x + math.cos(aa) * d, y + math.sin(aa) * d))
                polyline(ctx, pts, 8, hexc('#ffcf5a'))
    if split <= 0:
        body()
    else:
        glow(ctx, x, y, r * 0.8, hexc('#ffd070'), 0.9)
        circle(ctx, x, y, r * 0.35 * (1 - split * 0.5), hexc('#fff0b0'))
        for k in range(pieces):
            a0 = 2 * math.pi * k / pieces + 0.2
            a1 = 2 * math.pi * (k + 1) / pieces + 0.2
            am = (a0 + a1) / 2
            ctx.save()
            off = split * r * (0.5 + 0.15 * (k % 3))
            ctx.translate(math.cos(am) * off, math.sin(am) * off)
            ctx.translate(x, y)
            ctx.rotate(split * 0.3 * (1 if k % 2 else -1))
            ctx.translate(-x, -y)
            ctx.new_path()
            ctx.move_to(x, y)
            ctx.arc(x, y, r, a0, a1)
            ctx.close_path()
            ctx.clip()
            body()
            radial(ctx, x, y, r * 0.6, hexc('#ff6a10'), 0.9)
            ctx.restore()


def rock_platform(ctx, x, y, w, t, heat=1.0):
    pts = [(x - w, y), (x - w * 0.8, y - 30), (x + w * 0.85, y - 26), (x + w, y), (x + w * 0.5, y + 140),
           (x, y + 220), (x - w * 0.6, y + 120)]
    fill_poly(ctx, pts, hexc('#3a2a22'))
    fill_poly(ctx, [(x - w, y), (x - w * 0.8, y - 30), (x + w * 0.85, y - 26), (x + w, y)],
              mix(hexc('#5aa236'), hexc('#2a1008'), heat))
    for k in range(5):
        line(ctx, (x - w * 0.6 + k * w * 0.3, y + 10), (x - w * 0.5 + k * w * 0.3, y + 120 - k * 10), 4,
             alpha(hexc('#ff8a30'), 0.7 * heat))


def planet(ctx, x, y, r, c, ring=False, bands=False):
    if ring:
        ellipse_path(ctx, x, y, r * 2.1, r * 0.5, -0.3)
        ctx.set_line_width(r * 0.18)
        src(ctx, hexc('#d8c8a0'))
        ctx.stroke()
    circle(ctx, x, y, r, c)
    if bands:
        ctx.save()
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.clip()
        for k in range(5):
            rect(ctx, x - r, y - r + k * r * 0.42, 2 * r, r * 0.16, mul(c, 0.78))
        ctx.restore()
    ctx.save()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.clip()
    circle(ctx, x + r * 0.45, y + r * 0.35, r, (0, 0, 0, 0.35))
    ctx.restore()


R_GX = random.Random(5)
GALAXY = []
for _i in range(1400):
    arm = _i % 2
    tpar = R_GX.uniform(0.05, 1.0)
    ang = arm * math.pi + tpar * 4.4
    d = 40 + tpar * 520
    jx, jy = R_GX.gauss(0, 30 + 40 * tpar), R_GX.gauss(0, 30 + 40 * tpar)
    GALAXY.append((math.cos(ang) * d + jx, math.sin(ang) * d * 0.55 + jy, R_GX.uniform(1.0, 3.2), tpar))


def galaxy(ctx, x, y, t, blast=0.0, rotation=0.0):
    glow(ctx, x, y, 800, hexc('#7a4ad8'), 0.6)
    glow(ctx, x, y, 420, hexc('#ff9ad0'), 0.25)
    glow(ctx, x, y, 300, hexc('#ffe7b0'), 0.9)
    for (gx, gy, r, tp) in GALAXY:
        a = rotation * (1.2 - tp)
        rx = gx * math.cos(a) - gy * math.sin(a) / 0.55 * 0.55
        ry = gx * math.sin(a) * 0.55 + gy * math.cos(a)
        d = math.hypot(rx, ry) or 1
        push = blast * 900 * clamp(1 - d / 900 + 0.4)
        px = x + rx + rx / d * push
        py = y + ry + ry / d * push
        c = mix(hexc('#fff3d0'), hexc('#9ab8ff'), tp)
        circle(ctx, px, py, r * 1.5, alpha(c, 0.95))


def shock_ring(ctx, x, y, r, w, a, col=(1, 1, 1)):
    if a <= 0 or r <= 0:
        return
    ctx.new_path()
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_line_width(w)
    src(ctx, (col[0], col[1], col[2], a))
    ctx.stroke()
    ctx.new_path()
    ctx.arc(x, y, max(1, r - w * 1.2), 0, 2 * math.pi)
    ctx.set_line_width(w * 0.5)
    src(ctx, (col[0], col[1], col[2], a * 0.4))
    ctx.stroke()
