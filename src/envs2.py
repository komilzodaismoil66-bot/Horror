"""Episode 2 environments, built from the same palette / primitives as episode 1."""
import math
import random
import cairo
from engine import *
from envs import *

# wide versions of the episode-1 skylines (same generator settings -> same look, but long enough to scroll)
SKY_FAR2 = Skyline(11, -2500, 9000, 200, 520, col=hexc('#141a2e'), win=0.12, fire_p=0.35)
SKY_MID2 = Skyline(22, -2500, 9000, 260, 700, col=hexc('#0d1222'), win=0.2, fire_p=0.4)
COLD = hexc('#0a1630')
FOG = hexc('#33405c')


def street_ground_wide(ctx, y, t, camx, lit=1.0, fire=1.0):
    """street_ground() from episode 1, tiled so it follows the camera (lane dashes stay fixed in the world)."""
    off = round((camx - W / 2) / 260) * 260
    ctx.save()
    ctx.translate(off, 0)
    street_ground(ctx, y, t, lit, fire)
    ctx.restore()


def cold_tint(ctx, a):
    if a <= 0:
        return
    ctx.save()
    ctx.identity_matrix()
    ctx.set_source_rgba(0.04, 0.09, 0.2, a)
    ctx.paint()
    ctx.restore()


class Fog:
    """Soft drifting fog banks (world space)."""

    def __init__(self, seed, x0, x1, y, n=14, size=260, col=FOG):
        r = random.Random(seed)
        self.p = [(r.uniform(x0, x1), y + r.uniform(-60, 60), size * r.uniform(0.7, 1.4), r.uniform(10, 30),
                   r.uniform(0, 9)) for _ in range(n)]
        self.col = col

    def draw(self, ctx, t, a=0.35, dx=0.0):
        for (x, y, s, sp, ph) in self.p:
            xx = x + t * sp + dx
            radial(ctx, xx, y + math.sin(t * 0.3 + ph) * 12, s, self.col, a)


def dust(ctx, t, x0, y0, w, h, n=60, seed=3, a=0.5, col=(0.8, 0.85, 0.95), size=2.6):
    r = random.Random(seed)
    for i in range(n):
        ox, oy, ph, sp = r.random(), r.random(), r.random() * 6, r.uniform(0.2, 0.6)
        x = x0 + (ox * w + math.sin(t * sp + ph) * 30) % w
        y = y0 + (oy * h + t * 12 * sp) % h
        tw = 0.5 + 0.5 * math.sin(t * 2 + ph)
        circle(ctx, x, y, size * (0.6 + 0.6 * r.random()), (col[0], col[1], col[2], a * tw))


def lamp_post(ctx, x, ground, bend=0.0, lit=1.0):
    c = mul(hexc('#151a26'), lit)
    top = (x + math.sin(bend) * 420, ground - math.cos(bend) * 420)
    line(ctx, (x, ground), top, 12, c, cairo.LINE_CAP_BUTT)
    arm = (top[0] + math.cos(bend) * 70, top[1] + math.sin(bend) * 70)
    line(ctx, top, arm, 8, c)
    rect(ctx, arm[0] - 20, arm[1] - 4, 40, 14, c)


def rubble_pile(ctx, x, ground, w, h, seed=0, lit=1.0, rebar=True):
    r = random.Random(seed)
    # mound
    pts = [(x - w / 2, ground)]
    for i in range(1, 8):
        f = i / 8
        pts.append((x - w / 2 + w * f, ground - h * math.sin(math.pi * f) * r.uniform(0.75, 1.1)))
    pts.append((x + w / 2, ground))
    fill_poly(ctx, pts, mul(hexc('#1a1f2c'), lit))
    # slabs and bricks on top
    for i in range(int(w / 40)):
        f = r.uniform(0.1, 0.9)
        yy = ground - h * math.sin(math.pi * f) * r.uniform(0.6, 1.0)
        ctx.save()
        ctx.translate(x - w / 2 + w * f, yy)
        ctx.rotate(r.uniform(-0.7, 0.7))
        sw, sh = r.uniform(30, 110), r.uniform(14, 34)
        rect(ctx, -sw / 2, -sh / 2, sw, sh, mul(hexc('#262c3a'), lit * r.uniform(0.8, 1.3)))
        rect(ctx, -sw / 2, -sh / 2, sw, 4, mul(hexc('#3a4254'), lit))
        ctx.restore()
    if rebar:
        for i in range(2):
            a = (x - w * 0.2 + i * w * 0.3, ground - h * 0.6)
            b = (a[0] + r.uniform(-60, 60), a[1] - r.uniform(60, 130))
            line(ctx, a, b, 5, mul(hexc('#5a3a26'), lit))


def overturned_car(ctx, x, ground, s, t, lit=1.0, tilt=0.0):
    """Car lying on its roof. Chassis top at ground-125*s, wheels up to ground-165*s."""
    ctx.save()
    ctx.translate(x, ground)
    ctx.rotate(tilt)
    ctx.translate(0, -165 * s)
    ctx.scale(1, -1)
    draw_car(ctx, 0, 0, s, t, mul(hexc('#3b4660'), 0.75 * lit), burning=0.0, wreck=0.0)
    ctx.restore()
    # scorch, broken glass
    for i in range(6):
        circle(ctx, x - 150 * s + i * 60 * s, ground - 4, 5, (0.6, 0.7, 0.85, 0.35 * lit))


# ---------------------------------------------------------------- outskirts
def dead_tree(ctx, x, ground, h, seed, lit=1.0):
    r = random.Random(seed)
    c = mul(hexc('#0b0f19'), lit)

    def branch(p, ang, L, w, d):
        q = (p[0] + math.sin(ang) * L, p[1] - math.cos(ang) * L)
        line(ctx, p, q, w, c)
        if d > 0:
            for k in range(2):
                branch(q, ang + r.uniform(-0.8, 0.8), L * r.uniform(0.55, 0.75), w * 0.65, d - 1)
    branch((x, ground), r.uniform(-0.1, 0.1), h * 0.45, 14, 4)


def power_pole(ctx, x, ground, h=520, lean=0.0, lit=1.0):
    c = mul(hexc('#0d111c'), lit)
    top = (x + math.sin(lean) * h, ground - math.cos(lean) * h)
    line(ctx, (x, ground), top, 12, c, cairo.LINE_CAP_BUTT)
    line(ctx, (top[0] - 60, top[1] + 30), (top[0] + 60, top[1] + 26), 8, c)
    return top


def wire(ctx, a, b, sag, lit=1.0):
    ctx.new_path()
    ctx.move_to(*a)
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + sag)
    ctx.curve_to(a[0] + (m[0] - a[0]) * 0.8, m[1], b[0] - (b[0] - m[0]) * 0.8, m[1], *b)
    ctx.set_line_width(2.5)
    src(ctx, mul(hexc('#0d111c'), lit))
    ctx.stroke()


def outskirts(ctx, t, horizon=1150, lit=1.0, city_glow=1.0):
    vgrad(ctx, -2000, -800, 6000, horizon + 800, [(0, hexc('#050912')), (0.55, hexc('#0e1a33')),
                                                  (1, hexc('#22314f'))])
    moon(ctx, 760, 330, 40, 0.85)
    # far burning city on the left horizon
    glow(ctx, 0, horizon - 60, 700, FIRE1, 0.35 * city_glow)
    ctx.save()
    ctx.translate(-260, horizon)
    ctx.scale(0.42, 0.42)
    SKY_FAR2.draw(ctx, 0, t, 0, 0.9 * city_glow, 0.6)
    ctx.restore()
    for i, x in enumerate((-40, 120, 260)):
        radial(ctx, x, horizon - 300 - i * 60, 260, hexc('#1d1b22'), 0.6)
    # rolling wasteland
    ctx.new_path()
    ctx.move_to(-2000, horizon)
    for i in range(0, 41):
        x = -2000 + i * 150
        ctx.line_to(x, horizon + 10 * math.sin(i * 0.9) + 6 * math.sin(i * 2.3))
    ctx.line_to(4000, 4000)
    ctx.line_to(-2000, 4000)
    ctx.close_path()
    src(ctx, mul(hexc('#121a2a'), lit))
    ctx.fill()
    vgrad(ctx, -2000, horizon, 6000, 1200, [(0, mul(hexc('#18223a'), lit)), (1, mul(hexc('#070a12'), lit))])


def bunker_exterior(ctx, t, x, ground, s=1.0, lit=1.0, rubble=1.0, gap_open=True, sign_glow=0.0):
    """Half-buried shelter: grassy mound with a concrete portal facing left. Returns door rect (world)."""
    ctx.save()
    ctx.translate(x, ground)
    ctx.scale(s, s)
    # mound
    ctx.new_path()
    ctx.move_to(-120, 0)
    ctx.curve_to(-60, -330, 520, -360, 760, 0)
    ctx.close_path()
    src(ctx, mul(hexc('#141c22'), lit))
    ctx.fill()
    for i in range(18):
        gx = -80 + i * 45
        gy = -300 * math.sin(math.pi * min(1, max(0, (gx + 120) / 880))) + 6
        line(ctx, (gx, gy), (gx + 6, gy - 18), 3, mul(hexc('#1c2a26'), lit))
    # concrete portal
    portal = [(-40, 0), (-40, -300), (300, -300), (300, 0)]
    fill_poly(ctx, portal, mul(hexc('#2b3240'), lit))
    rect(ctx, -60, -330, 380, 40, mul(hexc('#353d4e'), lit))
    for k in range(4):
        line(ctx, (-40, -240 + k * 60), (300, -240 + k * 60), 2, mul(hexc('#222834'), lit))
    line(ctx, (10, -300), (40, -180), 2, mul(hexc('#1b202b'), lit))
    line(ctx, (240, -60), (270, -150), 2, mul(hexc('#1b202b'), lit))
    # sign plate
    rect(ctx, 30, -318, 200, 34, mul(hexc('#7a1c1c'), lit * (1 + 0.6 * sign_glow)))
    text(ctx, 'УБЕЖИЩЕ', 130, -293, 26, mul(hexc('#e8e2d0'), lit * (1 + 0.3 * sign_glow)), font='DejaVu Sans Bold')
    # steel door
    dx, dy, dw, dh = 40, -250, 180, 250
    rect(ctx, dx - 10, dy - 10, dw + 20, dh + 10, mul(hexc('#1a1f28'), lit))
    rect(ctx, dx, dy, dw, dh, mul(hexc('#3a4636'), lit))
    for (rx, ry) in ((12, 12), (dw - 12, 12), (12, dh - 12), (dw - 12, dh - 12)):
        circle(ctx, dx + rx, dy + ry, 4, mul(hexc('#556050'), lit))
    circle(ctx, dx + dw / 2, dy + dh / 2, 30, mul(hexc('#2a3226'), lit))
    ctx.new_path()
    ctx.arc(dx + dw / 2, dy + dh / 2, 30, 0, 2 * math.pi)
    ctx.set_line_width(6)
    src(ctx, mul(hexc('#606a58'), lit))
    ctx.stroke()
    if gap_open:
        fill_poly(ctx, [(dx + 6, dy + 4), (dx + 120, dy + 4), (dx + 90, dy + 70), (dx + 6, dy + 90)],
                  hexc('#010103'))
    ctx.restore()
    return (x + 40 * s, ground - 250 * s, 180 * s, 250 * s)


def door_rubble(ctx, x, ground, s=1.0, lit=1.0, seed=7):
    """Rubble covering most of the shelter door (front layer)."""
    ctx.save()
    ctx.translate(x, ground)
    ctx.scale(s, s)
    r = random.Random(seed)
    ctx.new_path()
    ctx.move_to(-160, 0)
    ctx.curve_to(-80, -150, 40, -200, 130, -175)
    ctx.curve_to(220, -160, 300, -120, 380, 0)
    ctx.close_path()
    src(ctx, mul(hexc('#1b202c'), lit))
    ctx.fill()
    for i in range(26):
        px = r.uniform(-120, 340)
        top = -180 * math.sin(math.pi * min(1, max(0, (px + 160) / 540)))
        py = r.uniform(top, 0)
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(r.uniform(-0.9, 0.9))
        kind = r.random()
        if kind < 0.45:
            w, h = r.uniform(40, 120), r.uniform(16, 36)
            rect(ctx, -w / 2, -h / 2, w, h, mul(hexc('#2a3040'), lit * r.uniform(0.8, 1.25)))
            rect(ctx, -w / 2, -h / 2, w, 4, mul(hexc('#3c4456'), lit))
        elif kind < 0.65:
            rect(ctx, -60, -6, 120, 12, mul(hexc('#3a2a1e'), lit))        # plank
        elif kind < 0.78:
            circle(ctx, 0, 0, 26, mul(hexc('#0b0b0d'), lit))               # tyre
            circle(ctx, 0, 0, 12, mul(hexc('#1b1f28'), lit))
        else:
            ellipse(ctx, 0, 0, 34, 24, mul(hexc('#111418'), lit))          # trash bag
            line(ctx, (-4, -22), (4, -30), 3, mul(hexc('#222222'), lit))
        ctx.restore()
    line(ctx, (60, -150), (20, -260), 6, mul(hexc('#5a3a26'), lit))
    line(ctx, (200, -140), (260, -230), 6, mul(hexc('#5a3a26'), lit))
    ctx.restore()


# ---------------------------------------------------------------- bunker interior (world coords)
ROOM = dict(x0=120, x1=960, ceil=1060, floor=1500)
DOOR_IN = (200, 1500 - 300, 190, 300)          # x, y, w, h on the back wall


def bunker_room(ctx, t, lit=1.0, door_open=0.0, outside_light=0.0, lantern=0.0):
    x0, x1, yc, yf = ROOM['x0'], ROOM['x1'], ROOM['ceil'], ROOM['floor']
    # back wall concrete panels
    rect(ctx, x0, yc, x1 - x0, yf - yc, mul(hexc('#1f2735'), lit))
    for i in range(int((x1 - x0) / 140) + 1):
        line(ctx, (x0 + i * 140, yc), (x0 + i * 140, yf), 3, mul(hexc('#18202c'), lit))
    rect(ctx, x0, yf - 120, x1 - x0, 120, mul(hexc('#1a2a2c'), lit))
    line(ctx, (x0, yf - 120), (x1, yf - 120), 3, mul(hexc('#24383a'), lit))
    # stains / cracks
    r = random.Random(4)
    for i in range(6):
        x = r.uniform(x0 + 40, x1 - 40)
        y = r.uniform(yc + 60, yf - 200)
        ellipse(ctx, x, y, r.uniform(20, 60), r.uniform(30, 90), mul(hexc('#18202b'), lit))
    # pipes along the ceiling
    rect(ctx, x0, yc + 20, x1 - x0, 18, mul(hexc('#33302c'), lit))
    rect(ctx, x0, yc + 46, x1 - x0, 10, mul(hexc('#2c3440'), lit))
    for i in range(5):
        rect(ctx, x0 + 60 + i * 180, yc + 14, 10, 46, mul(hexc('#1c1c20'), lit))
    # door (back wall) with outside light
    dx, dy, dw, dh = DOOR_IN
    rect(ctx, dx - 14, dy - 14, dw + 28, dh + 14, mul(hexc('#161b24'), lit))
    rect(ctx, dx, dy, dw, dh, mix(hexc('#020306'), hexc('#3a5280'), outside_light))
    ww = dw * (1 - door_open)
    rect(ctx, dx, dy, ww, dh, mul(hexc('#3a4636'), lit))
    if ww > 40:
        rect(ctx, dx + 10, dy + 12, ww - 20, dh - 24, mul(hexc('#333e30'), lit))
        circle(ctx, dx + ww / 2, dy + dh / 2, 28, mul(hexc('#2a3226'), lit))
        ctx.new_path()
        ctx.arc(dx + ww / 2, dy + dh / 2, 28, 0, 2 * math.pi)
        ctx.set_line_width(6)
        src(ctx, mul(hexc('#606a58'), lit))
        ctx.stroke()
    # poster
    rect(ctx, 430, 1150, 110, 150, mul(hexc('#5a4a36'), lit))
    rect(ctx, 440, 1160, 90, 60, mul(hexc('#7a2a22'), lit))
    for k in range(4):
        rect(ctx, 442, 1232 + k * 14, 86, 6, mul(hexc('#3a3026'), lit))
    # shelves with supplies
    sx = 580
    for k in range(3):
        rect(ctx, sx, 1200 + k * 90, 150, 10, mul(hexc('#3a2a1e'), lit))
    for k, (cx, cc) in enumerate(((600, '#9aa0a6'), (630, '#c0392b'), (668, '#2c6fb8'), (700, '#9aa0a6'),
                                  (610, '#2c6fb8'), (650, '#4a5a40'), (690, '#c0392b'))):
        row = k // 4
        rect(ctx, cx - 12, 1200 + row * 90 - 42, 24, 42, mul(hexc(cc), lit * 0.8))
    line(ctx, (sx, 1180), (sx, 1400), 6, mul(hexc('#3a2a1e'), lit))
    line(ctx, (sx + 150, 1180), (sx + 150, 1400), 6, mul(hexc('#3a2a1e'), lit))
    # bunk bed
    bx = 780
    for yy in (1300, 1420):
        rect(ctx, bx, yy, 170, 22, mul(hexc('#2c3a66'), lit * 0.8))
        rect(ctx, bx, yy + 22, 170, 8, mul(hexc('#222830'), lit))
    line(ctx, (bx + 4, 1220), (bx + 4, yf), 7, mul(hexc('#30363e'), lit))
    line(ctx, (bx + 166, 1220), (bx + 166, yf), 7, mul(hexc('#30363e'), lit))
    # gas mask on a hook
    circle(ctx, 400, 1180, 4, mul(hexc('#555555'), lit))
    ellipse(ctx, 400, 1218, 22, 30, mul(hexc('#2a3226'), lit))
    circle(ctx, 392, 1210, 7, mul(hexc('#6a7a8a'), lit))
    circle(ctx, 408, 1210, 7, mul(hexc('#6a7a8a'), lit))
    circle(ctx, 400, 1240, 9, mul(hexc('#1a1f18'), lit))
    # table + lantern
    rect(ctx, 420, 1400, 140, 12, mul(hexc('#3a2a1e'), lit))
    line(ctx, (430, 1412), (430, yf), 6, mul(hexc('#2a1e16'), lit))
    line(ctx, (550, 1412), (550, yf), 6, mul(hexc('#2a1e16'), lit))
    lx, ly = 490, 1400
    rect(ctx, lx - 18, ly - 10, 36, 10, mul(hexc('#2a2a2a'), lit))
    rrect(ctx, lx - 14, ly - 54, 28, 44, 6, mix(mul(hexc('#3a3a30'), lit), hexc('#ffd68a'), lantern))
    rect(ctx, lx - 16, ly - 60, 32, 8, mul(hexc('#2a2a2a'), lit))
    ctx.new_path()
    ctx.arc(lx, ly - 64, 12, math.pi, 2 * math.pi)
    ctx.set_line_width(3)
    src(ctx, mul(hexc('#2a2a2a'), lit))
    ctx.stroke()
    if lantern > 0:
        circle(ctx, lx, ly - 30, 6 + 2 * math.sin(t * 12), (1, 0.85, 0.5, lantern))
    # floor
    rect(ctx, x0 - 400, yf, x1 - x0 + 800, 60, mul(hexc('#161b24'), lit))
    rect(ctx, x0 - 400, yf, x1 - x0 + 800, 5, mul(hexc('#262d3a'), lit))
    return (lx, ly - 32)


def earth_section(ctx, t, surface=700, lit=1.0):
    """Cross-section: soil around the bunker room + entrance shaft."""
    x0, x1, yc, yf = ROOM['x0'], ROOM['x1'], ROOM['ceil'], ROOM['floor']
    vgrad(ctx, -2000, surface, 5000, 2600, [(0, mul(hexc('#151820'), lit)), (0.3, mul(hexc('#0f1118'), lit)),
                                             (1, mul(hexc('#07080c'), lit))])
    r = random.Random(2)
    for i in range(70):
        x = r.uniform(-1500, 2600)
        y = r.uniform(surface + 30, surface + 2200)
        ellipse(ctx, x, y, r.uniform(8, 26), r.uniform(5, 14), mul(hexc('#1c2029'), lit), r.uniform(0, 3))
    # concrete shell
    rect(ctx, x0 - 40, yc - 40, x1 - x0 + 80, yf - yc + 100, mul(hexc('#2a303c'), lit))
    # entrance shaft from the door up to the surface
    dx, dy, dw, dh = DOOR_IN
    rect(ctx, dx - 40, surface - 10, dw + 80, dy - surface + 10, mul(hexc('#2a303c'), lit))
    rect(ctx, dx, surface, dw, dy - surface, mul(hexc('#0b0e14'), lit))
    for k in range(int((dy - surface) / 40)):
        line(ctx, (dx + 20, surface + 20 + k * 40), (dx + dw - 20, surface + 20 + k * 40), 4,
             mul(hexc('#30363e'), lit))
