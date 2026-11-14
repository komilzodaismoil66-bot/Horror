"""'Поезд в 03:17' environments: abandoned metro station, the train, the carriage, stairs, street, phone UI."""
import math
import random
import cairo
from engine import *

# ---------------------------------------------------------------- palette
TILE = hexc('#3b4a47')
TILE_L = hexc('#4a5a56')
LAMP = hexc('#d8f0e4')
WARM = hexc('#ffd98a')
RED_LED = hexc('#ff2a22')
TRAIN_C = hexc('#2e4a6c')
TRAIN_D = hexc('#1e3350')

PLAT = 1244          # platform edge (top of the platform floor)
FLOOR = 1500         # where people stand on the platform
WALL_TOP = 250
TRACK = 1225         # train wheels / rails level


def lamp_flicker(t, i, steady=False):
    if steady:
        return 0.55
    v = noise(t * 9 + i * 13.1, 40 + i)
    base = 0.85 if i % 3 else 0.6
    if i % 4 == 1 and v > 0.35:
        return 0.08
    return base + 0.15 * v


# ---------------------------------------------------------------- station
def station(ctx, t, x0=-2000, x1=4000, steady=False, lit=1.0, clock=None, peel=True, portal_x=3000):
    """Platform side view. clock = (x, text, seconds, colon_on, glitch)."""
    # far wall
    rect(ctx, x0, WALL_TOP, x1 - x0, 1130 - WALL_TOP, mul(TILE, lit))
    for gx in range(int(x0 // 60) * 60, int(x1), 60):
        line(ctx, (gx, WALL_TOP), (gx, 1130), 2, mul(hexc('#2f3c3a'), lit))
    for gy in range(WALL_TOP, 1130, 40):
        line(ctx, (x0, gy), (x1, gy), 2, mul(hexc('#2f3c3a'), lit))
    rect(ctx, x0, 900, x1 - x0, 230, mul(hexc('#2b3634'), lit))
    line(ctx, (x0, 900), (x1, 900), 6, mul(hexc('#58403a'), lit))
    if peel:
        r = random.Random(3)
        for i in range(int((x1 - x0) / 260)):
            px = x0 + i * 260 + r.uniform(0, 160)
            py = r.uniform(WALL_TOP + 80, 860)
            pts = []
            n = 9
            rr = r.uniform(30, 80)
            for k in range(n):
                a = 2 * math.pi * k / n
                d = rr * r.uniform(0.55, 1.2)
                pts.append((px + math.cos(a) * d * 1.4, py + math.sin(a) * d))
            fill_poly(ctx, pts, mul(hexc('#262e2d'), lit))
            fill_poly(ctx, [(p[0] * 0.8 + px * 0.2, p[1] * 0.8 + py * 0.2) for p in pts], mul(hexc('#33302c'), lit))
    # exit sign and old adverts
    for i, ax in enumerate(range(int(x0) + 300, int(x1), 1200)):
        if ax > portal_x - 400:
            break
        rect(ctx, ax, 520, 260, 170, mul(hexc('#1e2524'), lit))
        rect(ctx, ax + 12, 532, 236, 146, mul(hexc('#4a4a3e') if i % 2 else hexc('#3a2c2a'), lit * 0.8))
        line(ctx, (ax + 40, 560), (ax + 200, 650), 3, mul(hexc('#2a2a26'), lit))
    # tunnel portal at the right end
    if portal_x < x1:
        rect(ctx, portal_x, WALL_TOP - 200, x1 - portal_x + 200, 1400, mul(hexc('#141a1a'), lit))
        ctx.new_path()
        ctx.move_to(portal_x + 120, TRACK + 10)
        ctx.line_to(portal_x + 120, 560)
        ctx.curve_to(portal_x + 120, 300, portal_x + 1100, 300, portal_x + 1100, 560)
        ctx.line_to(portal_x + 1100, TRACK + 10)
        ctx.close_path()
        src(ctx, hexc('#010102'))
        ctx.fill()
    # track bed
    rect(ctx, x0, 1130, x1 - x0, PLAT - 1130, hexc('#0b0d0e'))
    for sx in range(int(x0 // 90) * 90, int(x1), 90):
        rect(ctx, sx, 1205, 50, 12, hexc('#1a1716'))
    line(ctx, (x0, 1196), (x1, 1196), 5, mul(hexc('#5c5f66'), lit))
    line(ctx, (x0, 1214), (x1, 1214), 5, mul(hexc('#5c5f66'), lit))
    # platform
    rect(ctx, x0, PLAT, x1 - x0, 900, mul(hexc('#2a2c30'), lit))
    rect(ctx, x0, PLAT, x1 - x0, 14, mul(hexc('#b8a030'), lit * 0.8))
    rect(ctx, x0, PLAT + 14, x1 - x0, 8, mul(hexc('#141518'), lit))
    for gx in range(int(x0 // 180) * 180, int(x1), 180):
        line(ctx, (gx, PLAT + 22), (gx - 60, 2000), 2, mul(hexc('#222428'), lit))
    # ceiling + lamps
    rect(ctx, x0, -600, x1 - x0, WALL_TOP + 600, hexc('#0d1111'))
    lamps = []
    for i, lx in enumerate(range(int(x0 // 520) * 520, int(x1), 520)):
        if lx > portal_x:
            continue
        f = lamp_flicker(t, i, steady) * lit
        line(ctx, (lx + 90, WALL_TOP - 120), (lx + 90, WALL_TOP - 40), 3, hexc('#1a1a1a'))
        rrect(ctx, lx, WALL_TOP - 44, 180, 22, 6, mix(hexc('#2a302e'), LAMP, f))
        lamps.append((lx + 90, WALL_TOP - 30, f))
    if clock is not None:
        draw_station_clock(ctx, *clock)
    return lamps


def draw_station_clock(ctx, x, txt, secs=None, colon=True, glitch=0.0, y=360, s=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    line(ctx, (-80, -160), (-80, -60), 4, hexc('#1a1a1a'))
    line(ctx, (80, -160), (80, -60), 4, hexc('#1a1a1a'))
    rrect(ctx, -200, -70, 400, 150, 14, hexc('#1b1d1f'))
    rrect(ctx, -184, -56, 368, 122, 8, hexc('#070505'))
    shown = txt if colon else txt.replace(':', ' ')
    ox = 0
    if glitch > 0:
        ox = noise(glitch * 40, 3) * 12
    glow(ctx, 0, 6, 260, RED_LED, 0.25)
    text(ctx, shown, -20 + ox, 46, 104, RED_LED, font='DejaVu Sans Mono Bold')
    if secs is not None:
        text(ctx, f'{secs:02d}', 140, 46, 46, mul(RED_LED, 0.85), font='DejaVu Sans Mono Bold')
    if glitch > 0:
        for i in range(3):
            yy = -40 + (glitch * 300 + i * 37) % 100
            rect(ctx, -184, yy, 368, 5, (1, 0.2, 0.2, 0.35))
    ctx.restore()


def column(ctx, x, lit=1.0):
    rect(ctx, x - 60, -600, 120, 2600, mul(hexc('#151a1a'), lit))
    rect(ctx, x - 60, -600, 18, 2600, mul(hexc('#202726'), lit))


# ---------------------------------------------------------------- train
CAR_L = 1500


def draw_train(ctx, xh, t, ncars=4, doors=0.0, inside=0.6, lit=1.0, hands=0.0, dissolve=0.0, faces=True,
               head_lights=1.0, door_glow=None):
    """Train facing left; cab nose at xh, cars extend to the right. Returns door centres (world x)."""
    top, bot = 300, TRACK - 4
    door_xs = []
    for c in range(ncars):
        cx = xh + c * (CAR_L + 30)
        # body
        ctx.save()
        if dissolve > 0:
            # dissolving from the tail towards the head
            cut = xh + (ncars * (CAR_L + 30)) * (1 - dissolve)
            ctx.rectangle(-5000, -2000, cut + 5000, 6000)
            ctx.clip()
        if c == 0:
            ctx.new_path()
            ctx.move_to(cx + 180, top)
            ctx.line_to(cx + CAR_L, top)
            ctx.line_to(cx + CAR_L, bot)
            ctx.line_to(cx, bot)
            ctx.line_to(cx, top + 260)
            ctx.curve_to(cx, top + 60, cx + 60, top, cx + 180, top)
            ctx.close_path()
        else:
            rrect_path(ctx, cx, top, CAR_L, bot - top, 30)
        src(ctx, mul(TRAIN_C, lit))
        ctx.fill()
        rect(ctx, cx + (40 if c == 0 else 0), bot - 150, CAR_L - (40 if c == 0 else 0), 70, mul(TRAIN_D, lit))
        rect(ctx, cx + (20 if c == 0 else 0), top + 110, CAR_L - (20 if c == 0 else 0), 10, mul(hexc('#c9b98a'), lit * 0.6))
        # windows and doors
        for k in range(4):
            dx = cx + 170 + k * 360
            if c == 0 and k == 0:
                continue
            # window
            wx = dx + 205 if k < 3 else None
            if wx is not None and wx + 120 < cx + CAR_L:
                rrect(ctx, wx, top + 160, 120, 230, 14, mix(hexc('#0b0c0e'), WARM, inside * 0.55))
                if faces and inside > 0.2:
                    for j in range(2):
                        hx = wx + 30 + j * 60
                        circle(ctx, hx, top + 330, 22, (0.05, 0.05, 0.06, 0.85))
                        rrect(ctx, hx - 28, top + 350, 56, 60, 16, (0.05, 0.05, 0.06, 0.85))
            # door
            dw, dh = 240, 760
            door_xs.append(dx + dw / 2)
            ry = bot - dh - 10
            rect(ctx, dx - 6, ry - 6, dw + 12, dh + 12, mul(hexc('#1a2a40'), lit))
            gap = dw * 0.5 * doors
            rect(ctx, dx + dw / 2 - gap, ry, gap * 2, dh, mix(hexc('#0b0c0e'), door_glow or WARM, inside * 0.6))
            for side in (-1, 1):
                px = dx + dw / 2 + side * gap
                pw = dw / 2
                x_ = px if side > 0 else px - pw
                rect(ctx, x_, ry, pw, dh, mul(hexc('#3a5878'), lit))
                rrect(ctx, x_ + 20, ry + 70, pw - 40, 300, 10, mix(hexc('#0b0c0e'), WARM, inside * 0.45))
            # hands squeezing out of the closing doors
            if hands > 0 and doors < 0.6:
                r = random.Random(c * 10 + k)
                for j in range(5):
                    hy = ry + 120 + j * 120 + r.uniform(-30, 30)
                    reach = hands * r.uniform(60, 200) * (0.6 + 0.4 * math.sin(t * 9 + j))
                    sgn = -1 if j % 2 else 1
                    a = (dx + dw / 2, hy)
                    b = (dx + dw / 2 + sgn * reach * 0.4 - reach * 0.8, hy + r.uniform(-40, 40))
                    taper(ctx, a, b, 24, 20, mul(hexc('#8c96a0'), lit))
                    for f in range(4):
                        ang = math.pi + (f - 1.5) * 0.35 + math.sin(t * 12 + f + j) * 0.2
                        line(ctx, b, (b[0] + math.cos(ang) * 30, b[1] + math.sin(ang) * 30), 6,
                             mul(hexc('#8c96a0'), lit))
                    circle(ctx, b[0], b[1], 13, mul(hexc('#8c96a0'), lit))
        ctx.restore()
        # coupling
        rect(ctx, cx + CAR_L, bot - 120, 30, 60, hexc('#111111'))
    # cab: windshield, headlights, route plate
    if dissolve < 0.98:
        rrect(ctx, xh + 30, top + 120, 110, 220, 16, hexc('#06080a'))
        rect(ctx, xh + 60, top + 30, 120, 50, hexc('#0a0a0a'))
        text(ctx, '03:17', xh + 120, top + 68, 32, RED_LED, font='DejaVu Sans Mono Bold')
        if head_lights > 0:
            for hy in (bot - 210,):
                circle(ctx, xh + 26, hy, 22, mix(hexc('#444444'), hexc('#fffbe8'), head_lights))
                glow(ctx, xh + 10, hy, 260, hexc('#fff3c8'), 0.5 * head_lights)
    return door_xs


def train_front(ctx, cx, cy, s, t, lights=1.0, lit=1.0):
    """Cab seen head-on (for the hook / tunnel shots)."""
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(s, s)
    rrect(ctx, -330, -460, 660, 900, 120, mul(TRAIN_C, lit))
    rrect(ctx, -300, -380, 600, 280, 50, hexc('#05070a'))
    line(ctx, (0, -380), (0, -100), 12, mul(TRAIN_C, lit))
    rect(ctx, -330, 120, 660, 90, mul(TRAIN_D, lit))
    rect(ctx, -110, -440, 220, 50, hexc('#0a0a0a'))
    text(ctx, '03:17', 0, -403, 40, RED_LED, font='DejaVu Sans Mono Bold')
    for sx in (-1, 1):
        circle(ctx, sx * 220, 40, 46, mix(hexc('#333333'), hexc('#fffbe8'), lights))
    rect(ctx, -330, 380, 660, 60, hexc('#0a0a0a'))
    ctx.restore()
    if lights > 0:
        for sx in (-1, 1):
            glow(ctx, cx + sx * 220 * s, cy + 40 * s, 420 * s, hexc('#fff3c8'), 0.7 * lights)


def tunnel_view(ctx, t, lit=1.0):
    """Looking straight into the black tunnel."""
    rect(ctx, -3000, -3000, 8000, 8000, hexc('#030405'))
    for i in range(8, 0, -1):
        s = 0.72 ** i
        w, h = 1500 * s, 1700 * s
        ctx.new_path()
        ctx.rectangle(540 - w / 2, 1000 - h / 2, w, h)
        ctx.set_line_width(14 * s)
        src(ctx, mul(hexc('#151c1c'), lit * (0.9 ** i)))
        ctx.stroke()
    for sx in (-1, 1):
        line(ctx, (540 + sx * 60, 1080), (540 + sx * 700, 2600), 8, mul(hexc('#3a3d44'), lit))


# ---------------------------------------------------------------- carriage interior (front view of the far wall)
CF = 1500          # carriage floor


def carriage(ctx, t, x0=-1500, x1=3000, lit=1.0, moving=0.0, flick=True, red=0.0):
    wall = mix(hexc('#5d6352'), hexc('#5a2222'), red)
    rect(ctx, x0, CF - 940, x1 - x0, 940, mul(wall, lit))
    rect(ctx, x0, CF - 1100, x1 - x0, 170, mul(hexc('#2e3128'), lit))
    # ceiling light strip
    fl = 1.0
    if flick:
        v = noise(t * 7, 5)
        fl = 0.35 if v > 0.55 else 0.9 + 0.1 * v
    rect(ctx, x0, CF - 960, x1 - x0, 26, mix(hexc('#3a3a30'), hexc('#fff0c0'), fl * lit))
    # windows (black tunnel, streaks when moving)
    for wx in range(int(x0 // 520) * 520, int(x1), 520):
        rrect(ctx, wx + 40, CF - 820, 400, 240, 20, hexc('#07080a'))
        if moving > 0:
            for k in range(3):
                sx = wx + 40 + ((t * 2200 * moving + k * 170 + wx) % 400)
                line(ctx, (sx, CF - 760 + k * 60), (sx + 90, CF - 760 + k * 60), 4, (1, 0.85, 0.55, 0.5 * moving))
        rect(ctx, wx + 40, CF - 590, 400, 14, mul(hexc('#3a3c32'), lit))
    # handrail + poles
    line(ctx, (x0, CF - 880), (x1, CF - 880), 10, mul(hexc('#9aa0a6'), lit * 0.8))
    for px in range(int(x0 // 780) * 780 + 390, int(x1), 780):
        line(ctx, (px, CF - 880), (px, CF), 10, mul(hexc('#a2a8ae'), lit * 0.8))
    # bench
    rect(ctx, x0, CF - 330, x1 - x0, 200, mul(hexc('#6a3b2e'), lit * 0.9))
    rect(ctx, x0, CF - 140, x1 - x0, 40, mul(hexc('#7a4434'), lit))
    rect(ctx, x0, CF - 100, x1 - x0, 100, mul(hexc('#2a2420'), lit))
    # floor
    rect(ctx, x0, CF, x1 - x0, 800, mul(hexc('#2b2620'), lit))
    rect(ctx, x0, CF, x1 - x0, 8, mul(hexc('#3a3228'), lit))
    return fl


def carriage_door(ctx, x, lit=1.0, open_=1.0, outside=None):
    """Doorway in the far wall (front view): outside = colour seen through it."""
    w, h = 300, 900
    rect(ctx, x - w / 2 - 14, CF - h - 14, w + 28, h + 14, mul(hexc('#3a3c32'), lit))
    rect(ctx, x - w / 2, CF - h, w, h, outside or hexc('#0a0d0e'))
    g = w / 2 * open_
    rect(ctx, x - w / 2, CF - h, w / 2 - g, h, mul(hexc('#4a6a8a'), lit))
    rect(ctx, x + g, CF - h, w / 2 - g, h, mul(hexc('#4a6a8a'), lit))


# ---------------------------------------------------------------- stairs (side view, going up to the right)
def stairs(ctx, t, lit=1.0, exit_light=1.0, flick=True):
    rect(ctx, -2000, -2000, 6000, 6000, hexc('#0a0d0f'))
    rect(ctx, -2000, -800, 6000, 2600, mul(hexc('#2c3634'), lit))
    for gx in range(-2000, 4000, 60):
        line(ctx, (gx, -800), (gx, 1800), 2, mul(hexc('#24302e'), lit))
    # exit opening at the top right
    glow(ctx, 2300, -150, 900, hexc('#7f9cd8'), 0.45 * exit_light)
    rect(ctx, 2050, -500, 600, 420, mix(hexc('#0a0d10'), hexc('#4a5f8a'), exit_light))
    # steps from (-600, 1700) up to (2100, -80)
    n = 30
    pts = [(-600, 1700)]
    x, y = -600, 1700
    for i in range(n):
        y -= 1780 / n
        pts.append((x, y))
        x += 2700 / n
        pts.append((x, y))
    fill_poly(ctx, pts + [(x, 2600), (-600, 2600)], mul(hexc('#3a3f44'), lit))
    polyline(ctx, pts, 5, mul(hexc('#5a6068'), lit), cairo.LINE_CAP_BUTT, cairo.LINE_JOIN_MITER)
    # handrail
    line(ctx, (-600, 1500), (2100, -280), 10, mul(hexc('#6a4a30'), lit))
    for i in range(10):
        f = i / 9
        line(ctx, (-600 + 2700 * f, 1700 - 1780 * f), (-600 + 2700 * f, 1500 - 1780 * f), 5, mul(hexc('#40464e'), lit))
    # lamp
    fl = lamp_flicker(t, 2) if flick else 0.7
    rrect(ctx, 600, 300, 160, 22, 6, mix(hexc('#2a302e'), LAMP, fl * lit))
    return fl


def stair_point(f):
    """Point on the stairs (feet), f=0 bottom, 1 top."""
    return (-600 + 2700 * f, 1700 - 1780 * f)


# ---------------------------------------------------------------- street + metro entrance
def street(ctx, t, lit=1.0, sign='МЕТРО', sign_red=0.0, rumble=0.0, entrance_glow=0.0):
    vgrad(ctx, -3000, -1500, 8000, 2900, [(0, hexc('#04060c')), (0.75, hexc('#101a30')), (1, hexc('#1c2640'))])
    r = random.Random(5)
    x = -2200
    while x < 3600:
        w = r.uniform(220, 420)
        h = r.uniform(500, 1100)
        rect(ctx, x, 1400 - h, w, h + 10, mul(hexc('#0b0f1a'), lit))
        for i in range(int(w // 60)):
            for j in range(int(h // 80)):
                if r.random() < 0.08:
                    rect(ctx, x + 20 + i * 60, 1400 - h + 30 + j * 80, 26, 36, (1, 0.85, 0.5, 0.5 * lit))
        x += w + r.uniform(10, 60)
    # road + sidewalk
    rect(ctx, -3000, 1400, 8000, 800, mul(hexc('#15171c'), lit))
    rect(ctx, -3000, 1400, 8000, 140, mul(hexc('#262a30'), lit))
    rect(ctx, -3000, 1540, 8000, 10, mul(hexc('#3a3e46'), lit))
    for i in range(-10, 20):
        rect(ctx, i * 300, 1720, 160, 12, mul(hexc('#55554a'), lit))
    # lamp posts
    lights = []
    for lx in (-1300, -100, 1500, 2700):
        line(ctx, (lx, 1470), (lx, 700), 12, mul(hexc('#1c1f26'), lit))
        line(ctx, (lx, 700), (lx + 120, 690), 8, mul(hexc('#1c1f26'), lit))
        f = 0.9 + 0.1 * noise(t * 3 + lx, 2)
        if rumble > 0 and noise(t * 20 + lx, 9) > 0.3:
            f *= 0.2
        rect(ctx, lx + 100, 690, 60, 14, mix(hexc('#333333'), hexc('#ffe9b0'), f * lit))
        lights.append((lx + 130, 700, f))
    # metro entrance pavilion
    px, pw = 300, 900
    rect(ctx, px, 900, pw, 520, mul(hexc('#2a2e36'), lit))
    rect(ctx, px - 40, 860, pw + 80, 50, mul(hexc('#1c2028'), lit))
    for k in range(3):
        rect(ctx, px + 80 + k * 260, 1000, 220, 410, mix(hexc('#0a0e12'), hexc('#3a6a5a'), 0.3 + 0.7 * entrance_glow))
        line(ctx, (px + 190 + k * 260, 1000), (px + 190 + k * 260, 1410), 4, mul(hexc('#1c2028'), lit))
    if entrance_glow > 0:
        glow(ctx, px + pw / 2, 1250, 700, hexc('#fff3c8'), 0.35 * entrance_glow)
    # sign board
    sb = (px + 60, 760, pw - 120, 100)
    rect(ctx, sb[0], sb[1], sb[2], sb[3], hexc('#0b0b0e'))
    if sign_red > 0:
        g = sign_red
        glow(ctx, px + pw / 2, 810, 520, RED_LED, 0.35 * g)
    col = mix(hexc('#e8e8f0'), RED_LED, sign_red)
    size = 62 if len(sign) < 10 else 40
    text(ctx, sign, px + pw / 2, 810 + size * 0.36, size, col)
    # "M" pole
    line(ctx, (px - 160, 1470), (px - 160, 780), 10, mul(hexc('#1c1f26'), lit))
    circle(ctx, px - 160, 740, 60, hexc('#c8202a'))
    text(ctx, 'М', px - 160, 765, 70, hexc('#ffffff'))
    return lights


# ---------------------------------------------------------------- phone UI
def phone(ctx, x, y, s, screen_fn, lit=1.0, ang=0.0, hand=True, skin=hexc('#c89a72')):
    """A phone held in a hand, screen drawn by screen_fn(ctx, w, h) in local screen coords."""
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(s, s)
    w, h = 420, 860
    if hand:
        circle(ctx, -w / 2 + 10, 140, 70, mul(skin, lit))
    rrect(ctx, -w / 2 - 18, -h / 2 - 18, w + 36, h + 36, 56, hexc('#0b0c10'))
    ctx.save()
    rrect_path(ctx, -w / 2, -h / 2, w, h, 42)
    ctx.clip()
    ctx.translate(-w / 2, -h / 2)
    screen_fn(ctx, w, h)
    ctx.restore()
    rrect(ctx, -60, -h / 2 + 12, 120, 24, 12, hexc('#000000'))
    if hand:
        for k in range(3):
            rrect(ctx, w / 2 - 6, -60 + k * 70, 60, 54, 26, mul(skin, lit))
        rrect(ctx, -w / 2 - 40, 60, 60, 160, 28, mul(skin, lit))
    ctx.restore()


def screen_bg(ctx, w, h, c=hexc('#0d1424')):
    vgrad(ctx, 0, 0, w, h, [(0, c), (1, mul(c, 0.5))])


def screen_status(ctx, w, time_txt='03:17'):
    text(ctx, time_txt, 60, 46, 26, (1, 1, 1, 0.9), font='DejaVu Sans Bold')
    rect(ctx, w - 80, 30, 44, 18, (1, 1, 1, 0.8))


def screen_call(ctx, w, h, t, state='incoming', name='НЕИЗВЕСТНЫЙ', sub='входящий вызов'):
    screen_bg(ctx, w, h, hexc('#1a1d2c'))
    screen_status(ctx, w)
    circle(ctx, w / 2, 260, 80, hexc('#3a3f52'))
    circle(ctx, w / 2, 240, 30, hexc('#6a7088'))
    ellipse(ctx, w / 2, 300, 50, 28, hexc('#6a7088'))
    text(ctx, name, w / 2, 420, 34, (1, 1, 1, 1))
    text(ctx, sub, w / 2, 466, 24, (0.75, 0.78, 0.85, 1), font='DejaVu Sans')
    if state == 'incoming':
        p = 1 + 0.08 * math.sin(t * 10)
        circle(ctx, 110, 720, 46 * p, hexc('#e03a3a'))
        circle(ctx, w - 110, 720, 46 * p, hexc('#30c060'))
        rect(ctx, w - 130, 712, 40, 16, (1, 1, 1, 1))
        rect(ctx, 90, 712, 40, 16, (1, 1, 1, 1))
    elif state == 'active':
        text(ctx, '00:0' + str(min(9, int(t % 10))), w / 2, 520, 26, (0.7, 0.9, 0.7, 1), font='DejaVu Sans')
        circle(ctx, w / 2, 720, 46, hexc('#e03a3a'))
    else:
        text(ctx, 'ВЫЗОВ ЗАВЕРШЁН', w / 2, 560, 30, hexc('#ff5050'))


def screen_lock(ctx, w, h, t, big='03:17', red=0.0):
    screen_bg(ctx, w, h, mix(hexc('#14203a'), hexc('#3a0a0a'), red))
    text(ctx, 'пятница, 13', w / 2, 160, 26, (1, 1, 1, 0.8), font='DejaVu Sans')
    col = mix(hexc('#ffffff'), RED_LED, red)
    text(ctx, big, w / 2, 300, 120, col, font='DejaVu Sans Bold')
