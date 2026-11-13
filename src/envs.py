"""Environments: burning city, fire, smoke, bedroom, stairwell, street props."""
import math
import random
import cairo
from engine import *

FIRE1 = hexc('#ff4a12')
FIRE2 = hexc('#ff9a26')
FIRE3 = hexc('#ffe27a')
NIGHT0 = hexc('#070a16')
NIGHT1 = hexc('#101a33')


# ---------------------------------------------------------------- fire / smoke / embers
def flame(ctx, x, y, w, h, t, seed=0, a=1.0, glow_=True):
    """Cluster of flame tongues standing on (x, y), width w, height h."""
    if glow_:
        glow(ctx, x, y - h * 0.4, max(w, h) * 1.6, FIRE1, 0.45 * a)
    n = max(3, int(w / 22))
    for layer, (col, sc) in enumerate(((FIRE1, 1.0), (FIRE2, 0.72), (FIRE3, 0.42))):
        for i in range(n):
            fx = x - w / 2 + w * (i + 0.5) / n
            ph = seed * 3.1 + i * 1.7
            hh = h * sc * (0.55 + 0.45 * abs(math.sin(i * 2.3 + seed))) * (0.8 + 0.25 * noise(t * 6 + ph, seed + i))
            ww = w / n * 1.25 * (sc + 0.25)
            sway = noise(t * 4 + ph, seed + 40 + i) * ww * 0.9
            tip = (fx + sway, y - hh)
            ctx.new_path()
            ctx.move_to(fx - ww / 2, y)
            ctx.curve_to(fx - ww * 0.65, y - hh * 0.45, tip[0] - ww * 0.15, tip[1] + hh * 0.3, tip[0], tip[1])
            ctx.curve_to(tip[0] + ww * 0.15, tip[1] + hh * 0.3, fx + ww * 0.65, y - hh * 0.45, fx + ww / 2, y)
            ctx.close_path()
            src(ctx, alpha(col, a * (0.92 if layer == 0 else 0.95)))
            ctx.fill()


class Smoke:
    def __init__(self, x, y, seed=0, n=16, size=60, rise=70, life=7.0, drift=30, col=hexc('#1d1b22'),
                 under=FIRE1, spread=1.0):
        self.x, self.y, self.seed, self.n, self.size = x, y, seed, n, size
        self.rise, self.life, self.drift, self.col, self.under, self.spread = rise, life, drift, col, under, spread
        r = random.Random(seed)
        self.offs = [r.random() for _ in range(n)]
        self.dx = [r.uniform(-1, 1) for _ in range(n)]

    def draw(self, ctx, t, a=1.0):
        for i in range(self.n):
            age = ((t / self.life) + self.offs[i]) % 1.0
            px = self.x + self.dx[i] * self.size * 0.4 * self.spread + age * self.drift * self.life + \
                noise(t * 0.4 + i, self.seed) * self.size * 0.3
            py = self.y - age * self.rise * self.life
            r = self.size * (0.6 + age * 2.2)
            fa = (1 - age) * min(1, age * 6) * a
            c = mix(self.under, self.col, clamp(age * 4))
            radial(ctx, px, py, r, c, 0.75 * fa)


def embers(ctx, t, x0, y0, w, h, n=40, seed=1, a=1.0, speed=60):
    r = random.Random(seed)
    for i in range(n):
        ox, ph, sp = r.random(), r.random(), r.uniform(0.6, 1.4)
        life = h / (speed * sp)
        age = ((t / life) + ph) % 1.0
        px = x0 + ox * w + math.sin(t * 2 + i) * 18 + age * 40
        py = y0 + h - age * h
        rr = 2 + 2.5 * r.random()
        al = a * (1 - age) * (0.6 + 0.4 * math.sin(t * 12 + i))
        circle(ctx, px, py, rr, alpha(FIRE2, clamp(al)))


# ---------------------------------------------------------------- city skyline
class Skyline:
    def __init__(self, seed, x0, x1, hmin, hmax, wmin=70, wmax=170, col=hexc('#0c1120'), win=0.25,
                 fire_p=0.3, gap=(0, 12)):
        r = random.Random(seed)
        self.b = []
        x = x0
        while x < x1:
            w = r.uniform(wmin, wmax)
            h = r.uniform(hmin, hmax)
            wins = []
            cols = max(1, int((w - 20) / 26))
            rows = int((h - 30) / 34)
            for cx in range(cols):
                for ry in range(rows):
                    if r.random() < win:
                        wins.append((cx, ry, r.random()))
            top = r.choice(['flat', 'flat', 'antenna', 'step', 'tank'])
            fire = r.random() < fire_p
            fires = []
            if fire:
                fires.append(('roof', r.uniform(0.2, 0.8), r.uniform(0.5, 1.2)))
                for k in range(r.randint(1, 3)):
                    fires.append(('win', r.uniform(0.1, 0.9), r.uniform(0.15, 0.8)))
            self.b.append(dict(x=x, w=w, h=h, wins=wins, cols=cols, rows=rows, top=top, fires=fires,
                               seed=r.randint(0, 999), shade=r.uniform(0.8, 1.15)))
            x += w + r.uniform(*gap)
        self.col = col

    def draw(self, ctx, base_y, t, ox=0.0, fire_a=1.0, light=1.0, win_col=hexc('#ffcf6b'), burning=True,
             collapse=None):
        for b in self.b:
            x = b['x'] + ox
            if x > W + 400 or x + b['w'] < -400:
                continue
            y = base_y - b['h']
            c = mul(self.col, b['shade'])
            rect(ctx, x, y, b['w'], b['h'] + 2, c)
            if b['top'] == 'antenna':
                line(ctx, (x + b['w'] * 0.6, y), (x + b['w'] * 0.6, y - 60), 4, c)
            elif b['top'] == 'step':
                rect(ctx, x + b['w'] * 0.2, y - 30, b['w'] * 0.5, 31, c)
            elif b['top'] == 'tank':
                rect(ctx, x + b['w'] * 0.6, y - 26, 28, 27, c)
            # windows
            for (cx, ry, v) in b['wins']:
                wx = x + 14 + cx * 26
                wy = y + 22 + ry * 34
                if b['fires'] and burning:
                    fl = 0.55 + 0.45 * noise(t * 5 + v * 20, b['seed'])
                    wc = mix(FIRE1, FIRE3, v * 0.6)
                    rect(ctx, wx, wy, 13, 18, alpha(wc, fl * light))
                else:
                    on = v > 0.35
                    if on:
                        rect(ctx, wx, wy, 13, 18, alpha(win_col, 0.55 * light * (0.6 + 0.4 * v)))
            if burning:
                for kind, fx, fs in b['fires']:
                    if kind == 'roof':
                        flame(ctx, x + b['w'] * fx, y + 4, b['w'] * 0.55 * fs, 110 * fs, t, b['seed'], fire_a)
                    else:
                        wy = y + b['h'] * fs
                        flame(ctx, x + b['w'] * fx, wy, 40, 60, t, b['seed'] + 7, fire_a * 0.9)

    def fire_points(self, base_y, ox=0.0):
        pts = []
        for b in self.b:
            for kind, fx, fs in b['fires']:
                if kind == 'roof':
                    pts.append((b['x'] + ox + b['w'] * fx, base_y - b['h'], fs))
        return pts


def night_sky(ctx, glow_amt=1.0, top=hexc('#060914'), mid=hexc('#141a33'), low=hexc('#5a2216'),
              x=0, y=0, w=W, h=H, horizon=0.75):
    vgrad(ctx, x, y, w, h, [(0, top), (horizon * 0.6, mid), (horizon, mix(mid, low, glow_amt)),
                            (1, mix(mid, low, glow_amt))])


def moon(ctx, x, y, r, a=1.0):
    glow(ctx, x, y, r * 4, hexc('#9fb4ff'), 0.25 * a)
    circle(ctx, x, y, r, (0.86, 0.88, 0.92, a))
    circle(ctx, x - r * 0.3, y - r * 0.2, r * 0.18, (0.75, 0.77, 0.82, a))
    circle(ctx, x + r * 0.25, y + r * 0.3, r * 0.12, (0.75, 0.77, 0.82, a))


# ---------------------------------------------------------------- the burning city (wide)
SKY_FAR = Skyline(11, -400, 1600, 200, 520, col=hexc('#141a2e'), win=0.12, fire_p=0.35)
SKY_MID = Skyline(22, -400, 1600, 260, 700, col=hexc('#0d1222'), win=0.2, fire_p=0.4)
SKY_NEAR = Skyline(33, -400, 1700, 300, 820, wmin=140, wmax=260, col=hexc('#070a14'), win=0.25, fire_p=0.45)
CITY_SMOKE = [Smoke(x, 1100, seed=i, n=14, size=70, rise=60, life=9, drift=14) for i, x in
              enumerate((90, 380, 640, 900))]


def burning_city(ctx, t, base_y=1400, glow_amt=1.0, ox=0.0, smoke=True, layers=3, fire_a=1.0):
    night_sky(ctx, glow_amt, horizon=(base_y - 200) / H)
    moon(ctx, 780 + ox * 0.05, 330, 46, 0.8)
    if smoke:
        for s in CITY_SMOKE:
            s.x0 = getattr(s, 'x0', s.x)
            s.x = s.x0 + ox * 0.2
            s.y = base_y - 420
            s.draw(ctx, t, 0.85)
    glow(ctx, W / 2 + ox * 0.1, base_y - 100, 900, FIRE1, 0.35 * glow_amt)
    SKY_FAR.draw(ctx, base_y - 260, t, ox * 0.25, fire_a * 0.7, 0.6)
    if layers > 1:
        SKY_MID.draw(ctx, base_y - 120, t, ox * 0.5, fire_a * 0.85, 0.8)
    if layers > 2:
        SKY_NEAR.draw(ctx, base_y, t, ox, fire_a, 1.0)


# ---------------------------------------------------------------- cars
def draw_car(ctx, x, y, s, t, col=hexc('#3b4660'), burning=0.0, flip=1, wreck=0.0, seed=0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s * flip, s)
    dark = mul(col, 0.55)
    burnt = hexc('#1a1716')
    c = mix(col, burnt, burning)
    d = mix(dark, burnt, burning)
    # body
    body = [(-200, -40), (-195, -95), (-120, -105), (-70, -165), (70, -165), (120, -105), (200, -95), (205, -40)]
    ctx.save()
    ctx.rotate(math.radians(wreck * 4))
    fill_poly(ctx, body, c)
    fill_poly(ctx, [(-60, -155), (-5, -155), (-5, -108), (-104, -108)], mix(hexc('#2b3a55'), hexc('#ff8a2a'),
                                                                         burning * 0.6))
    fill_poly(ctx, [(5, -155), (62, -155), (106, -108), (5, -108)], mix(hexc('#2b3a55'), hexc('#ff8a2a'),
                                                                      burning * 0.6))
    rect(ctx, -200, -60, 405, 10, d)
    rect(ctx, 180, -90, 22, 14, hexc('#ffd27a') if burning < 0.5 else hexc('#3a2a20'))
    ctx.restore()
    for wx in (-125, 125):
        circle(ctx, wx, -38, 38, hexc('#0a0a0c'))
        circle(ctx, wx, -38, 18, mul(hexc('#4a4f5a'), 1 - burning * 0.6))
    ctx.restore()
    if burning > 0:
        flame(ctx, x - 20 * s * flip, y - 150 * s, 200 * s * burning, 230 * s * burning, t, seed)
        flame(ctx, x + 130 * s * flip, y - 100 * s, 110 * s, 120 * s * burning, t + 1.3, seed + 4)


# ---------------------------------------------------------------- bedroom
def bedroom(ctx, t, window_glow=0.5, lamp=1.0, shake=0.0, outside=True, curtain=1.0):
    """Night bedroom, side view. Floor at y=1380. Window on the right side."""
    wall = hexc('#18213b')
    vgrad(ctx, -600, -200, W + 1200, 1600, [(0, hexc('#0d1326')), (1, wall)])
    rect(ctx, -600, 1380, W + 1200, 700, hexc('#0d1120'))
    vgrad(ctx, -600, 1380, W + 1200, 40, [(0, hexc('#1a2238')), (1, hexc('#0d1120'))])
    rect(ctx, -600, 1350, W + 1200, 30, hexc('#121a30'))
    # window
    wx, wy, ww, wh = 600, 560, 380, 520
    if outside:
        ctx.save()
        ctx.rectangle(wx, wy, ww, wh)
        ctx.clip()
        ctx.translate(wx, wy)
        ctx.scale(ww / W, ww / W)
        burning_city(ctx, t, base_y=1500, glow_amt=0.4 + 0.6 * window_glow, layers=3, fire_a=window_glow,
                     smoke=window_glow > 0.2)
        ctx.restore()
    else:
        rect(ctx, wx, wy, ww, wh, hexc('#0b1020'))
    frame = hexc('#0a0e1c')
    for (a, b, c_, d) in ((wx - 14, wy - 14, ww + 28, 18), (wx - 14, wy + wh - 4, ww + 28, 24),
                          (wx - 14, wy - 14, 18, wh + 28), (wx + ww - 4, wy - 14, 18, wh + 28),
                          (wx + ww / 2 - 7, wy, 14, wh), (wx, wy + wh * 0.42, ww, 12)):
        rect(ctx, a, b, c_, d, frame)
    rect(ctx, wx - 40, wy + wh + 8, ww + 80, 22, hexc('#141a2e'))
    # glow from window onto room
    if window_glow > 0:
        fl = 0.8 + 0.2 * noise(t * 7, 3)
        glow(ctx, wx + ww / 2, wy + wh / 2, 700, FIRE1, 0.32 * window_glow * fl)
    # curtains
    sway = math.sin(t * 0.8) * 6
    for sx, x0 in ((-1, wx - 70), (1, wx + ww - 30)):
        pts = [(x0, wy - 50), (x0 + 100, wy - 50), (x0 + 100 + sway * sx * curtain, wy + wh + 140),
               (x0 + sway * sx * curtain, wy + wh + 140)]
        fill_poly(ctx, pts, hexc('#1f2742'))
        for k in range(3):
            line(ctx, (x0 + 25 + k * 25, wy - 40), (x0 + 25 + k * 25 + sway * sx, wy + wh + 130), 3,
                 hexc('#161d34'))
    rect(ctx, wx - 90, wy - 60, ww + 180, 12, hexc('#0b0f1d'))
    # picture frame
    rect(ctx, 150, 520, 200, 150, hexc('#0d1222'))
    rect(ctx, 165, 535, 170, 120, hexc('#1d2944'))
    fill_poly(ctx, [(165, 655), (230, 580), (280, 640), (305, 610), (335, 655)], hexc('#26345a'))
    # bed
    rect(ctx, 30, 1000, 24, 380, hexc('#2a1c18'))
    rrect(ctx, 30, 960, 70, 90, 14, hexc('#33221c'))
    rrect(ctx, 50, 1120, 520, 150, 20, hexc('#2c3a66'))
    rect(ctx, 60, 1260, 500, 120, hexc('#1c1414'))
    rect(ctx, 540, 1180, 24, 200, hexc('#2a1c18'))
    # nightstand + lamp
    nx = -170
    rect(ctx, nx - 80, 1150, 160, 230, hexc('#2a1d17'))
    rect(ctx, nx - 70, 1200, 140, 6, hexc('#1a110d'))
    rect(ctx, nx - 6, 1060, 12, 90, hexc('#3a3a42'))
    lampc = mix(hexc('#3a3040'), hexc('#f5d58a'), lamp)
    fill_poly(ctx, [(nx - 50, 1060), (nx + 50, 1060), (nx + 34, 990), (nx - 34, 990)], lampc)
    if lamp > 0:
        glow(ctx, nx, 1040, 520, hexc('#ffc46b'), 0.55 * lamp)
    # rug
    ellipse(ctx, 520, 1395, 260, 26, hexc('#2b1f2e'))


def bed_blanket(ctx, t, rise=0.0):
    """Blanket drawn over the sleeping hero."""
    pts = [(80, 1130), (200, 1095 - rise * 10), (380, 1100), (560, 1110), (570, 1270), (70, 1270)]
    ctx.new_path()
    ctx.move_to(*pts[0])
    ctx.curve_to(140, 1085, 260, 1080, 380, 1100)
    ctx.curve_to(480, 1110, 540, 1105, 568, 1130)
    ctx.line_to(570, 1270)
    ctx.line_to(70, 1270)
    ctx.close_path()
    src(ctx, hexc('#3b4f8c'))
    ctx.fill()
    for k in range(3):
        ctx.new_path()
        ctx.move_to(160 + k * 120, 1110)
        ctx.curve_to(170 + k * 120, 1160, 150 + k * 120, 1210, 165 + k * 120, 1265)
        ctx.set_line_width(4)
        src(ctx, hexc('#2c3c70'))
        ctx.stroke()


def pillow(ctx):
    rrect(ctx, 70, 1070, 150, 60, 28, hexc('#b8bfd6'))
    rrect(ctx, 80, 1100, 130, 22, 10, hexc('#9aa2bc'))


# ---------------------------------------------------------------- stairwell (cross-section)
FH = 460           # floor height
SW_W = 1080


def stair_flight(ctx, x0, y0, x1, y1, steps, col, under, thick=40):
    """Flight from (x0, y0) to (x1, y1) with step teeth on top."""
    pts = []
    dx = (x1 - x0) / steps
    dy = (y1 - y0) / steps
    x, y = x0, y0
    pts.append((x, y))
    for i in range(steps):
        y += dy
        pts.append((x, y))
        x += dx
        pts.append((x, y))
    bottom = [(x1, y1 + thick), (x0, y0 + thick)]
    fill_poly(ctx, pts + bottom, under)
    polyline(ctx, pts, 5, col, cairo.LINE_CAP_BUTT, cairo.LINE_JOIN_MITER)


def railing(ctx, x0, y0, x1, y1, h=110, n=10, col=hexc('#2a2f3c'), hand=hexc('#3a2a20')):
    for i in range(n + 1):
        f = i / n
        x = x0 + (x1 - x0) * f
        y = y0 + (y1 - y0) * f
        line(ctx, (x, y), (x, y - h), 4, col)
    line(ctx, (x0, y0 - h), (x1, y1 - h), 10, hand)


def door(ctx, x, y, w=150, h=300, num='', open_=0.0, col=hexc('#3a2a24'), lit=1.0):
    rect(ctx, x - 10, y - h - 10, w + 20, h + 10, mul(hexc('#0e1220'), lit))
    rect(ctx, x, y - h, w, h, hexc('#020306'))
    if open_ < 0.98:
        ww = w * (1 - open_)
        rect(ctx, x, y - h, ww, h, mul(col, lit))
        rect(ctx, x + 10, y - h + 12, max(0, ww - 20), h - 24, mul(col, 0.8 * lit))
        if ww > 30:
            circle(ctx, x + ww - 22, y - h * 0.48, 7, mul(hexc('#b6a26a'), lit))
    if num:
        rect(ctx, x + w / 2 - 22, y - h - 52, 44, 32, mul(hexc('#5a6070'), lit))
        text(ctx, num, x + w / 2, y - h - 27, 24, mul(hexc('#d7dbe4'), lit), font='DejaVu Sans Bold')


class Stairwell:
    """Multi-floor stairwell cross-section. Floor k landing level at y = base - k*FH (right side)."""

    def __init__(self, floors=6, base=1700):
        self.floors = floors
        self.base = base

    def level(self, k):
        return self.base - k * FH

    def mid(self, k):
        return self.base - k * FH - FH / 2

    def draw(self, ctx, t, k0=0, k1=None, lit=1.0, bulbs=None, window_glow=1.0, numbers=True, crack=True):
        if k1 is None:
            k1 = self.floors
        top = self.level(k1) - FH
        bot = self.base + 600
        upper = mul(hexc('#2a3248'), lit)
        lower = mul(hexc('#1b3038'), lit)
        # walls: lower half painted (classic stairwell), upper whitewash in blue shade
        rect(ctx, -400, top, SW_W + 800, bot - top, upper)
        for k in range(k0 - 1, k1 + 1):
            y = self.level(k)
            rect(ctx, -400, y - 210, SW_W + 800, 210, lower)
            line(ctx, (-400, y - 210), (SW_W + 400, y - 210), 4, mul(hexc('#203a44'), lit * 1.2))
            ym = self.mid(k)
            # mid landing window (left) with burning city glow
            if k < k1:
                wx, wy = 40, ym - 330
                rect(ctx, wx - 12, wy - 12, 204, 244, mul(hexc('#11151f'), lit))
                fl = 0.7 + 0.3 * noise(t * 5 + k, 7)
                vgrad(ctx, wx, wy, 180, 220, [(0, mul(hexc('#2a1220'), lit + 0.3)),
                                              (1, mix(hexc('#3a1a14'), hexc('#ff6a20'), 0.6 * window_glow * fl))])
                for i in range(4):
                    rect(ctx, wx + i * 45, wy + 120 + (i * 37 % 50), 40, 120, hexc('#0a0d16'))
                rect(ctx, wx + 84, wy, 12, 220, mul(hexc('#11151f'), lit))
                rect(ctx, wx, wy + 100, 180, 10, mul(hexc('#11151f'), lit))
                glow(ctx, wx + 90, wy + 110, 360, FIRE1, 0.22 * window_glow * fl)
            if numbers and k >= 0:
                text(ctx, str(k + 1), 930, y - 250, 90, mul(hexc('#5d7f86'), lit * 1.1), font='DejaVu Sans Bold')
        # cracks / peeling paint
        if crack:
            r = random.Random(5)
            for k in range(k0, k1):
                y = self.level(k)
                for i in range(3):
                    x = r.uniform(250, 850)
                    yy = y - r.uniform(240, 400)
                    pts = [(x, yy)]
                    for j in range(4):
                        pts.append((pts[-1][0] + r.uniform(-30, 30), pts[-1][1] + r.uniform(10, 30)))
                    polyline(ctx, pts, 2, mul(hexc('#151a28'), lit))
        # structure per floor
        for k in range(k0 - 1, k1 + 1):
            y = self.level(k)
            ym = self.mid(k)
            yn = self.level(k + 1)
            # back flight (mid landing -> next floor), darker
            stair_flight(ctx, 240, ym, 600, yn, 9, mul(hexc('#2c3346'), lit), mul(hexc('#141824'), lit))
            railing(ctx, 250, ym, 600, yn, col=mul(hexc('#202533'), lit), hand=mul(hexc('#2a2020'), lit))
            # landing (right) and mid landing (left)
            rect(ctx, 600, y, SW_W + 400 - 600, 46, mul(hexc('#3b4258'), lit))
            rect(ctx, 600, y, SW_W + 400 - 600, 6, mul(hexc('#525a72'), lit))
            rect(ctx, -400, ym, 640, 46, mul(hexc('#3b4258'), lit))
            rect(ctx, -400, ym, 640, 6, mul(hexc('#525a72'), lit))
            # apartment door on landing
            door(ctx, 760, y, num=str(10 + k * 3 + 2) if k >= 0 else '', lit=lit)
            # front flight (landing -> mid landing going up-left)
            stair_flight(ctx, 600, y, 240, ym, 9, mul(hexc('#5a6278'), lit), mul(hexc('#262c3c'), lit))
            railing(ctx, 590, y, 250, ym, col=mul(hexc('#3c4252'), lit), hand=mul(hexc('#5a3a26'), lit))
            # ceiling bulb
            bx, by = 520, y - FH + 50
            line(ctx, (bx, y - FH + 46), (bx, by + 40), 3, mul(hexc('#101010'), lit))
            on = 0.0
            if bulbs is not None:
                on = bulbs(k, t)
            circle(ctx, bx, by + 52, 14, mix(mul(hexc('#3a3a3a'), lit), hexc('#fff0b0'), on))
            if on > 0:
                glow(ctx, bx, by + 52, 420, hexc('#ffd88a'), 0.5 * on)

    def bulb_pos(self, k):
        return (520, self.level(k) - FH + 102)

    def flight_point(self, k, f):
        """Point on the front flight of floor k (f=0 at landing, 1 at mid landing)."""
        y = self.level(k)
        ym = self.mid(k)
        return (600 + (240 - 600) * f, y + (ym - y) * f)

    def back_point(self, k, f):
        ym = self.mid(k)
        yn = self.level(k + 1)
        return (240 + (600 - 240) * f, ym + (yn - ym) * f)


# ---------------------------------------------------------------- street pieces
def street_ground(ctx, y, t, lit=1.0, fire=1.0):
    rect(ctx, -800, y, W + 1600, H - y + 800, mul(hexc('#0c0f18'), lit))
    rect(ctx, -800, y, W + 1600, 26, mul(hexc('#262c3a'), lit))
    rect(ctx, -800, y + 26, W + 1600, 8, mul(hexc('#05070c'), lit))
    for i in range(-6, 12):
        rect(ctx, i * 260 + 40, y + 180, 140, 14, mul(hexc('#3a3a2a'), lit))
    vgrad(ctx, -800, y + 34, W + 1600, 300, [(0, alpha(FIRE1, 0.14 * fire)), (1, alpha(FIRE1, 0.0))])


def debris(ctx, y, seed=3, lit=1.0, n=14, x0=-200, x1=1300):
    r = random.Random(seed)
    for i in range(n):
        x = r.uniform(x0, x1)
        w = r.uniform(20, 70)
        h = r.uniform(10, 30)
        a = r.uniform(-0.5, 0.5)
        ctx.save()
        ctx.translate(x, y + r.uniform(10, 120))
        ctx.rotate(a)
        rect(ctx, -w / 2, -h / 2, w, h, mul(hexc('#1d2130'), lit * r.uniform(0.7, 1.2)))
        ctx.restore()
