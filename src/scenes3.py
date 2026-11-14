"""'Поезд в 03:17' — standalone mystical horror short. Shots timed to the narration clips."""
import math
import random
import cairo
from engine import *
from characters import walk_pose, run_pose
from chars3 import HERO, DOUBLE, PASS, HERO3, Toon
from envs3 import *
import scenes as ep1
from timeline3 import S, E, W as WT, CL, HOOK, T_DOUBLE, T_BLACK, TOTAL, caption_chunks

CAPS = caption_chunks()
RED = hexc('#ff2a2a')


def shake_env(t, ev, decay=3.0):
    return sum(st * math.exp(-(t - te) * decay) for te, st in ev if t >= te)


def glitch(ctx, a, t, col=(1, 0.2, 0.25)):
    if a <= 0:
        return
    ctx.save()
    ctx.identity_matrix()
    r = random.Random(int(t * 30))
    for i in range(int(4 + 8 * a)):
        y = r.uniform(0, H)
        h = r.uniform(4, 40)
        ctx.rectangle(0, y, W, h)
        src(ctx, (col[0], col[1], col[2], 0.12 * a * r.random()))
        ctx.fill()
        ctx.rectangle(r.uniform(-40, 40) * a, y, W, h * 0.3)
        src(ctx, (1, 1, 1, 0.08 * a))
        ctx.fill()
    ctx.restore()


def scan_tint(ctx, a, col=(0.02, 0.05, 0.04)):
    if a <= 0:
        return
    ctx.save()
    ctx.identity_matrix()
    ctx.set_source_rgba(col[0], col[1], col[2], a)
    ctx.paint()
    ctx.restore()


def big_text(ctx, s, y, size, col, a=1.0, sc=1.0):
    if a <= 0:
        return
    ctx.save()
    ctx.translate(W / 2, y)
    ctx.scale(sc, sc)
    text(ctx, s, 0, 0, size, alpha(col, a), outline=(0, 0, 0, a), ow=14)
    ctx.restore()


def pcam(ctx, x, z, t, shake=0.0, floor_y=1230, floor=FLOOR):
    """Platform camera: keeps the platform floor at a fixed screen height above the captions."""
    camera(ctx, x, floor - (floor_y - 960) / z, z, shake=shake, t=t)


def station_light(ctx, lamps, extra=(), amount=0.66):
    d = Darkness(ctx, amount, color=(0.0, 0.02, 0.02))
    for (x, y, f) in lamps:
        d.hole(x, y + 260, 700, 0.85 * f)
    for e in extra:
        d.hole(*e)
    d.apply()
    for (x, y, f) in lamps:
        glow(ctx, x, y + 10, 260, LAMP, 0.28 * f)


SEAT = 152


def ic(x, focus, z, sy=800):
    """Camera args that put world height `focus` at screen height `sy`."""
    return (x, focus + (960 - sy) / z, z)


HEAD_Y = 1180          # seated head height in the carriage
PASS_X = [-760, -600, -440, -280, -120, 40, 200, 360, 520, 860, 1020, 1180, 1340, 1500, 1660]
FREE_X = 700           # the free seat
DOUBLE_X = 860         # the double sits right of the free seat


def passengers(ctx, t, x_skip=(), heads_up=0.0, look=(-1, 0), lit=0.8, dbl=None, glow_eyes=True):
    for i, x in enumerate(PASS_X):
        if x in x_skip:
            continue
        if x == DOUBLE_X:
            if dbl is not None:
                dbl(ctx, x)
            continue
        p = PASS[i % len(PASS)]
        hu = heads_up
        P = dict(t=t + i * 0.37, facing=0, sit=SEAT, lit=lit, pale=0.35, blink=False,
                 head_down=1.0 - hu, eyes='glow' if (hu > 0.5 and glow_eyes) else 'closed', mouth='line',
                 look=look, head_tilt=-8 * hu * (1 if look[0] < 0 else -1))
        p.draw(ctx, x, CF, 0.92, P)


def double_pose(t, **kw):
    P = dict(t=t, facing=0, sit=SEAT, lit=0.95, watch=True, blink=False, eyes='open', mouth='line', look=(-1, 0))
    P.update(kw)
    return P


# =============================================================== 0. hook
def s_hook(ctx, t, lt, d):
    p = ease_in(seg(lt, 0.4, d - 0.2))
    camera(ctx, 540, 960, 1.0, shake=2 + 26 * p, t=t)
    tunnel_view(ctx, t)
    s = lerp(0.04, 2.6, p)
    train_front(ctx, 540, 1000 + 120 * p, s, t, lights=min(1, lt / 0.8))
    if lt < 1.2:
        draw_station_clock(ctx, 540, '03:17', None, int(lt * 3) % 2 == 0, glitch=lt, y=430, s=1.1)
    ctx.identity_matrix()
    post(ctx, t, vignette=1.1)
    for i, (s_, at, col, size) in enumerate((('КАЖДУЮ НОЧЬ В 03:17', 0.25, hexc('#ff3a30'), 78),
                                            ('НА ЗАБРОШЕННОЙ СТАНЦИИ', 1.3, hexc('#ffffff'), 60),
                                            ('ПОЯВЛЯЕТСЯ ПОЕЗД', 2.3, hexc('#ffd43b'), 84))):
        a = seg(lt, at, at + 0.15)
        big_text(ctx, s_, 1340 + i * 105, size, col, a, back_out(seg(lt, at, at + 0.3)))
    flash(ctx, seg(lt, d - 0.25, d) * 0.95)


# =============================================================== 1. legend
def s_timetable(ctx, t, lt, d):
    camera(ctx, 540, 900, lerp(1.0, 1.1, lt / d), t=t)
    rect(ctx, -500, -500, 2100, 2900, hexc('#0d1012'))
    rrect(ctx, 90, 330, 900, 1080, 20, hexc('#1a1e22'))
    rrect(ctx, 120, 360, 840, 1020, 12, hexc('#0b0d0f'))
    text(ctx, 'РАСПИСАНИЕ', 540, 450, 56, hexc('#e8d48a'))
    rows = ['23:40', '00:15', '00:52', '01:30', '02:05', '— — —', '03:17']
    for i, r in enumerate(rows):
        y = 560 + i * 110
        if r == '03:17':
            g = 0.5 + 0.5 * math.sin(t * 25) if noise(t * 6, 2) > 0 else 0
            a = g * (1 - seg(t, WT('A1', 'расписании'), WT('A1', 'расписании') + 0.4))
            text(ctx, r, 300, y, 64, (1, 0.2, 0.2, a), font='DejaVu Sans Mono Bold')
            text(ctx, '???', 720, y, 52, (1, 0.2, 0.2, a), font='DejaVu Sans Mono Bold')
            continue
        text(ctx, r, 300, y, 60, hexc('#f0d070'), font='DejaVu Sans Mono Bold')
        text(ctx, 'ОТПР.' if r[0] != '—' else '', 720, y, 44, hexc('#a09060'), font='DejaVu Sans Mono Bold')
    post(ctx, t)
    glitch(ctx, 0.6 * seg(t, WT('A1', 'расписании'), WT('A1', 'расписании') + 0.2), t)


def s_cctv(ctx, t, lt, d):
    camera(ctx, 540, 960, 1.0, t=t)
    rect(ctx, -500, -500, 2100, 2900, hexc('#08090a'))
    # monitor
    rrect(ctx, 60, 470, 960, 760, 30, hexc('#1c1e22'))
    ctx.save()
    rrect_path(ctx, 100, 510, 880, 680, 16)
    ctx.clip()
    ctx.translate(100, 510)
    ctx.scale(880 / 3000, 880 / 3000)
    ctx.translate(-100, -200)
    lamps = station(ctx, t, x0=-200, x1=3300, portal_x=2500)
    ctx.restore()
    # make it greyscale-ish + noise
    ctx.save()
    rrect_path(ctx, 100, 510, 880, 680, 16)
    ctx.clip()
    rect(ctx, 100, 510, 880, 680, (0.55, 0.65, 0.6, 0.35))
    r = random.Random(int(t * 24))
    for i in range(160):
        rect(ctx, r.uniform(100, 980), r.uniform(510, 1190), r.uniform(2, 8), 2, (1, 1, 1, r.uniform(0.1, 0.4)))
    if noise(t * 3, 4) > 0.2:
        yb = 510 + (t * 400 % 680)
        rect(ctx, 100, yb, 880, 30, (1, 1, 1, 0.12))
    if lt > d * 0.45:
        # where the train should be: only static
        sx = seg(lt, d * 0.45, d * 0.55)
        for i in range(60):
            rect(ctx, r.uniform(100, 980), r.uniform(700, 1000), r.uniform(20, 120), r.uniform(3, 10),
                 (1, 1, 1, 0.5 * sx * r.random()))
    ctx.restore()
    text(ctx, 'CAM 04', 150, 570, 34, (1, 1, 1, 0.9), font='DejaVu Sans Mono Bold', anchor='left')
    text(ctx, f'03:17:{int(lt * 2) % 60:02d}', 930, 570, 34, (1, 1, 1, 0.9), font='DejaVu Sans Mono Bold',
         anchor='right')
    if int(t * 2) % 2 == 0:
        circle(ctx, 160, 1150, 12, RED)
        text(ctx, 'REC', 186, 1162, 30, RED, font='DejaVu Sans Mono Bold', anchor='left')
    text(ctx, 'НЕТ СИГНАЛА', 540, 900, 60, (1, 1, 1, 0.8 * seg(lt, d * 0.5, d * 0.6)), font='DejaVu Sans Mono Bold')
    post(ctx, t)


def missing_poster(ctx, x, y, ang, style, t, lit=1.0, name='ПРОПАЛ'):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang + math.sin(t * 2 + x) * 0.01)
    rect(ctx, -150, -200, 300, 400, mul(hexc('#d8d2c0'), lit))
    text(ctx, name, 0, -150, 44, mul(hexc('#b01818'), lit))
    rect(ctx, -90, -120, 180, 170, mul(hexc('#8a8a84'), lit))
    ctx.save()
    ctx.rectangle(-90, -120, 180, 170)
    ctx.clip()
    Toon(style).draw(ctx, 0, 200, 0.6, dict(t=1, facing=0, lit=lit * 0.9, blink=False))
    ctx.restore()
    for k in range(4):
        rect(ctx, -110, 80 + k * 26, 220 - k * 30, 10, mul(hexc('#5a5850'), lit))
    circle(ctx, 0, -188, 8, hexc('#8a2020'))
    ctx.restore()


def s_missing(ctx, t, lt, d):
    camera(ctx, lerp(380, 700, lt / d), 900, 1.15, t=t)
    rect(ctx, -800, -500, 2800, 2900, hexc('#2a302e'))
    for gx in range(-800, 2000, 60):
        line(ctx, (gx, -500), (gx, 2400), 2, hexc('#232927'))
    r = random.Random(4)
    for i in range(9):
        x = -300 + (i % 5) * 330 + r.uniform(-30, 30)
        y = 520 + (i // 5) * 470 + r.uniform(-40, 40) + (160 if i % 2 else 0)
        missing_poster(ctx, x, y, r.uniform(-0.12, 0.12), PASSENGERS_ALL[i % len(PASSENGERS_ALL)], t,
                       lit=1 - 0.5 * seg(t, WT('A3', 'никогда'), WT('A3', 'никогда') + 1.5),
                       name='ПРОПАЛ' if i % 3 else 'ПРОПАЛА')
    d_ = Darkness(ctx, 0.6)
    d_.hole(lerp(380, 700, lt / d), 900, 700, 0.8)
    d_.apply()
    post(ctx, t)


from chars3 import PASSENGERS as PASSENGERS_ALL


def room(ctx, t, laptop=1.0, lit=1.0):
    rect(ctx, -800, -500, 2800, 2900, mul(hexc('#141a2c'), lit))
    rect(ctx, 620, 420, 360, 440, hexc('#070a14'))
    for i in range(6):
        rect(ctx, 640 + i * 55, 700 - (i * 37 % 120), 40, 160 + (i * 37 % 120), hexc('#0e1424'))
        if i % 2:
            rect(ctx, 650 + i * 55, 730, 10, 14, (1, 0.85, 0.5, 0.6))
    rect(ctx, 612, 412, 376, 12, hexc('#0b0e18'))
    rect(ctx, 794, 420, 10, 440, hexc('#0b0e18'))
    rect(ctx, -800, 1500, 2800, 900, mul(hexc('#100f14'), lit))
    rect(ctx, 80, 1150, 640, 30, mul(hexc('#3a2a20'), lit))       # desk
    rect(ctx, 100, 1180, 24, 320, mul(hexc('#2a1e16'), lit))
    rect(ctx, 680, 1180, 24, 320, mul(hexc('#2a1e16'), lit))
    # laptop
    fill_poly(ctx, [(380, 1150), (600, 1150), (620, 1160), (360, 1160)], hexc('#1a1c22'))
    ctx.save()
    ctx.translate(580, 1150)
    ctx.rotate(math.radians(-100 + 100 * (1 - laptop) * 0.95) if laptop < 1 else math.radians(-100))
    rect(ctx, 0, -6, 250, 12, hexc('#1a1c22'))
    ctx.restore()
    if laptop > 0.05:
        glow(ctx, 520, 1020, 520, hexc('#7fb0ff'), 0.45 * laptop)


def laptop_screen(ctx, t, a=1.0):
    """Close-up of the forum post on the laptop."""
    rrect(ctx, 80, 380, 920, 600, 24, hexc('#0b0c10'))
    rect(ctx, 110, 410, 860, 540, hexc('#e8ecf2'))
    rect(ctx, 110, 410, 860, 60, hexc('#2a3a5a'))
    text(ctx, 'ФОРУМ · ГОРОДСКИЕ ЛЕГЕНДЫ', 140, 450, 28, (1, 1, 1, 1), anchor='left')
    text(ctx, 'ПОЕЗД В 03:17. ЭТО ПРАВДА?', 140, 540, 40, hexc('#b01818'), anchor='left')
    for k in range(6):
        rect(ctx, 140, 580 + k * 44, 760 - (k * 97 % 260), 18, hexc('#9aa2b0'))
    text(ctx, 'ответов: 0', 140, 900, 26, hexc('#5a6070'), font='DejaVu Sans', anchor='left')


def s_room(ctx, t, lt, d):
    t_dec = WT('A4', 'решаешь')
    if t < WT('A4', 'истории', end=True):
        # close-up of the screen first
        camera(ctx, 540, 680, lerp(1.0, 1.15, lt / 2.5), t=t)
        rect(ctx, -500, -500, 2100, 2900, hexc('#06080e'))
        laptop_screen(ctx, t)
        glow(ctx, 540, 680, 700, hexc('#7fb0ff'), 0.15)
        post(ctx, t)
        return
    stand = ease_io(seg(t, t_dec, t_dec + 0.7))
    camera(ctx, 420, 1080, 1.55, t=t)
    room(ctx, t, laptop=1 - seg(t, t_dec + 0.6, t_dec + 1.0))
    P = dict(t=t, facing=1, lit=0.9, eyes='open', brows='angry' if t > t_dec else 'worried', mouth='line',
             look=(1, 0.2), legs=(lerp(85, 0, stand), lerp(85, 0, stand), lerp(85, 0, stand), lerp(85, 0, stand)),
             hip_dy=lerp(80, 0, stand), hand_f=(lerp(110, 10, stand), lerp(10, 150, stand)),
             hand_b=(lerp(100, 6, stand), lerp(20, 150, stand)))
    rect(ctx, 200, 1380, 120, 20, hexc('#2a2a30'))          # chair
    line(ctx, (260, 1400), (260, 1500), 8, hexc('#2a2a30'))
    HERO.draw(ctx, 250, 1500, 1.0, P)
    d_ = Darkness(ctx, 0.75)
    d_.hole(520, 1050, 520 * (1 - seg(t, t_dec + 0.6, t_dec + 1.0)) + 1, 0.9)
    d_.hole(800, 640, 400, 0.4)
    d_.apply()
    post(ctx, t)


# =============================================================== 2. the station
def s_descend(ctx, t, lt, d):
    f = 1 - lt / d * 0.55 - 0.3
    x, y = stair_point(f)
    camera(ctx, x + 80, y - 260, 1.25, shake=1.5, t=t)
    fl = stairs(ctx, t, lit=0.8, exit_light=0.6)
    P = dict(walk_pose(t * 1.3), t=t, facing=-1, lit=0.9, eyes='open', brows='worried', mouth='line', look=(1, 0.5),
             lean=-6)
    HERO.draw(ctx, x, y + 6, 1.0, P)
    d_ = Darkness(ctx, 0.85)
    d_.hole(680, 420, 700, 0.8 * fl)
    d_.hole(2300, -150, 900, 0.6)
    d_.apply()
    post(ctx, t)


def s_platform(ctx, t, lt, d):
    t_peel = WT('B3', 'на')
    if t < t_peel:
        z = lerp(0.62, 0.7, lt / 2)
        pcam(ctx, 900, z, t)
    else:
        p = ease_io(seg(t, t_peel, t_peel + 2.4))
        camera(ctx, lerp(300, 900, p), 640, 1.8, t=t)
    lamps = station(ctx, t, x0=-1600, x1=4200, clock=(1040, '03:16', None, True, 0))
    for cx in (-500, 1500, 3500):
        column(ctx, cx)
    station_light(ctx, lamps)
    post(ctx, t)
    scan_tint(ctx, 0.08)


def s_clock(ctx, t, lt, d):
    camera(ctx, 1040, 380, lerp(2.2, 2.6, lt / d), t=t)
    lamps = station(ctx, t, x0=-200, x1=2500, clock=(1040, '03:16', 50 + int(lt * 1.0), int(t * 2) % 2 == 0, 0))
    station_light(ctx, lamps, [(1040, 380, 500, 0.6)], 0.7)
    post(ctx, t)


def hero_platform(ctx, t, x, **kw):
    P = dict(t=t, facing=1, lit=0.85, eyes='open', brows='worried', mouth='line')
    P.update(kw)
    return HERO.draw(ctx, x, FLOOR, 1.0, P)


def s_wait(ctx, t, lt, d):
    pcam(ctx, 920, lerp(0.85, 0.92, lt / d), t)
    lamps = station(ctx, t, x0=-600, x1=3000, clock=(1040, '03:16', 56 + min(1, int(lt)), int(t * 2) % 2 == 0, 0))
    hero_platform(ctx, t, 820, look=(0.6, -1), head_tilt=-12, hip_dx=4 * math.sin(t * 1.5))
    column(ctx, 1700)
    station_light(ctx, lamps)
    post(ctx, t)
    scan_tint(ctx, 0.06)


def s_clock_stop(ctx, t, lt, d):
    t_stop = WT('B5', 'останавливаются')
    stopped = t > t_stop
    secs = 58 if t < t_stop - 0.6 else 59
    gl = seg(t, t_stop, t_stop + 0.1) * (1 - seg(t, t_stop + 0.5, t_stop + 1.0))
    camera(ctx, 1040, 380, 2.7, shake=6 * gl, t=t)
    lamps = station(ctx, t, x0=-200, x1=2500, steady=stopped,
                    clock=(1040, '03:16', secs, True if stopped else int(t * 2) % 2 == 0, gl))
    station_light(ctx, lamps, [(1040, 380, 500, 0.6)], 0.7)
    post(ctx, t)
    glitch(ctx, gl, t)


FROZEN_DUST = None


def s_silence(ctx, t, lt, d):
    pcam(ctx, 840, lerp(1.25, 1.5, ease_io(lt / d)), t, floor_y=1300)
    lamps = station(ctx, t, x0=-600, x1=3000, steady=True, clock=(1040, '03:16', 59, True, 0))
    hero_platform(ctx, t, 820, look=(-1, 0) if (lt % 2) < 1 else (1, 0), eyes='wide', mouth='o')
    # dust hanging motionless in the air
    r = random.Random(7)
    for i in range(70):
        circle(ctx, r.uniform(300, 1400), r.uniform(500, 1500), r.uniform(1.5, 3.2), (0.85, 0.9, 0.88, 0.45))
    station_light(ctx, lamps, amount=0.82)
    post(ctx, t, vignette=1.25)
    scan_tint(ctx, 0.1)


def s_light(ctx, t, lt, d):
    p = ease_in(seg(t, WT('B7', 'появляется') - 0.3, E('B7') + 1.2))
    pcam(ctx, lerp(2500, 2850, ease_io(lt / d)), 0.72, t, shake=2 + 4 * p)
    lamps = station(ctx, t, x0=-200, x1=4500, steady=True, portal_x=3000)
    hero_platform(ctx, t, 2450, look=(1, 0), eyes='wide', mouth='o', lit=0.7 + 0.4 * p,
                  rim=alpha(hexc('#fff3c8'), 0.6 * p))
    # light deep in the tunnel
    lx = 3600
    glow(ctx, lx, 900, 300 + 900 * p, hexc('#fff3c8'), 0.25 + 0.6 * p)
    circle(ctx, lx - 40, 1000, 8 + 20 * p, hexc('#fffbe8'))
    circle(ctx, lx + 40, 1000, 8 + 20 * p, hexc('#fffbe8'))
    station_light(ctx, lamps, [(lx, 950, 400 + 1500 * p, 0.4 + 0.6 * p)], 0.85)
    post(ctx, t)


def train_x(t):
    """Head position of the arriving train (decelerating), stopping with a door in front of the hero (x=820)."""
    t0, t1 = S('B8') - 0.2, WT('B8', 'перед') - 0.1
    p = clamp((t - t0) / (t1 - t0))
    stop = 820 - (170 + 360 + 120)         # door #2 of the first car centred on the hero
    return lerp(3600, stop, 1 - (1 - p) ** 2.6)


def s_arrive(ctx, t, lt, d):
    xh = train_x(t)
    stopped = t > WT('B8', 'перед') - 0.1
    pcam(ctx, 950, 0.68, t, shake=3 + 3 * (not stopped))
    lamps = station(ctx, t, x0=-1000, x1=4500, steady=True, portal_x=3000)
    draw_train(ctx, xh, t, inside=0.5, lit=0.9)
    hero_platform(ctx, t, 820, look=(1, -0.3), eyes='wide', mouth='o', lean=-4)
    if not stopped:
        r = random.Random(int(t * 30))
        for i in range(12):
            sx = xh + r.uniform(100, 1400)
            line(ctx, (sx, TRACK - 10), (sx - r.uniform(20, 60), TRACK - r.uniform(20, 60)), 3, (1, 0.8, 0.3, 0.9))
    station_light(ctx, lamps, [(xh - 200, TRACK - 210, 900, 0.8)], 0.8)
    post(ctx, t)


def s_doors(ctx, t, lt, d):
    op = ease_io(seg(t, S('B9') + 0.1, S('B9') + 1.4))
    xh = train_x(t)
    pcam(ctx, 820, lerp(1.0, 1.25, lt / d), t)
    lamps = station(ctx, t, x0=-600, x1=3000, steady=True)
    draw_train(ctx, xh, t, doors=op, inside=0.7, lit=0.9)
    hero_platform(ctx, t, 820, look=(0, -0.4), eyes='wide', mouth='o', facing=0, lit=0.8 + 0.3 * op,
                  rim=alpha(WARM, 0.4 * op))
    station_light(ctx, lamps, [(820, 900, 700 * op + 1, 0.9 * op)], 0.82)
    glow(ctx, 820, 900, 500, WARM, 0.25 * op)
    post(ctx, t)


# =============================================================== 3. passengers
def interior(ctx, t, cam, heads_up=0.0, dbl=None, red=0.0, moving=0.0, hero_fn=None, dark=0.55, look=(-1, 0)):
    camera(ctx, *cam, t=t)
    fl = carriage(ctx, t, red=red, moving=moving)
    carriage_door(ctx, -1100, open_=1.0, outside=hexc('#1a2422'))
    passengers(ctx, t, heads_up=heads_up, dbl=dbl, look=look)
    if hero_fn:
        hero_fn(ctx)
    d_ = Darkness(ctx, dark * (1.25 - 0.25 * fl), color=(0.02, 0.015, 0.0))
    d_.hole(cam[0], CF - 500, 1200, 0.6)
    d_.apply()
    return fl


def dbl_down(t, hu=0.0, **kw):
    def f(ctx, x):
        P = dict(head_down=1 - hu, eyes='closed' if hu < 0.5 else 'open')
        P.update(kw)
        DOUBLE.draw(ctx, x, CF, 0.92, double_pose(t, **P))
    return f


def s_inside(ctx, t, lt, d):
    p = ease_io(lt / d)
    interior(ctx, t, ic(lerp(-300, 500, p), CF, 0.85, 1230), dbl=dbl_down(t))
    post(ctx, t)


def s_heads(ctx, t, lt, d):
    p = ease_io(lt / d)
    interior(ctx, t, ic(lerp(-500, 300, p), HEAD_Y + 60, 1.6), dbl=dbl_down(t))
    post(ctx, t)


def s_approach(ctx, t, lt, d):
    p = ease_io(lt / d)
    hx = lerp(-1000, 520, ease_out(seg(lt, 0, d * 0.85)))
    walking = lt < d * 0.85

    def hero(ctx):
        HERO.draw(ctx, hx, CF + 120, 1.05, dict(walk_pose(t * 1.1, 0.7) if walking else {}, t=t, facing=1, lit=0.95,
                                                eyes='open', brows='worried', mouth='line', look=(1, 0.3)))
    interior(ctx, t, ic(lerp(-300, 600, p), CF + 120, 0.95, 1240), dbl=dbl_down(t), hero_fn=hero)
    post(ctx, t)


def hero_near(ctx, t, **kw):
    P = dict(t=t, facing=1, lit=0.95, eyes='open', brows='worried', mouth='line', look=(1, 0.4))
    P.update(kw)
    return HERO.draw(ctx, 520, CF + 120, 1.05, P)


def s_head_up(ctx, t, lt, d):
    hu = ease_io(seg(t, WT('C4', 'поднимает') - 0.2, E('C4') + 0.2))
    interior(ctx, t, ic(DOUBLE_X - 40, HEAD_Y, lerp(1.8, 2.2, lt / d), 760), dbl=dbl_down(t, hu, look=(-0.8, -0.3)),
             hero_fn=lambda c: hero_near(c, t))
    post(ctx, t)


def s_freeze(ctx, t, lt, d):
    interior(ctx, t, ic(560, 1215, 3.0, 720), dbl=dbl_down(t, 1, look=(-0.8, -0.3)),
             hero_fn=lambda c: hero_near(c, t, eyes='tiny', mouth='o', tremble=0.6))
    post(ctx, t, vignette=1.3)


def s_same(ctx, t, lt, d):
    p = ease_io(lt / d)
    interior(ctx, t, ic(lerp(640, 790, p), lerp(1300, 1230, p), lerp(1.4, 2.0, p), 780),
             dbl=dbl_down(t, 1, look=(-0.8, -0.3)), hero_fn=lambda c: hero_near(c, t, eyes='tiny', mouth='o'))
    post(ctx, t)


def s_compare(ctx, t, lt, d):
    # tilt down the double: hair -> hoodie -> jeans
    keys = [(S('C7'), 1215), (WT('C7', 'волосы'), 1215), (WT('C7', 'голубая') - 0.1, 1350), (WT('C7', 'чёрные') - 0.1, 1480),
            (E('C7') + 0.4, 1480)]
    cy = keys[0][1]
    for i in range(len(keys) - 1):
        if t >= keys[i][0]:
            cy = lerp(keys[i][1], keys[i + 1][1], ease_io(seg(t, keys[i][0], keys[i + 1][0])))
    interior(ctx, t, (DOUBLE_X, cy, 2.4), dbl=dbl_down(t, 1, look=(-0.8, -0.3)), dark=0.45)
    post(ctx, t)


def s_strange(ctx, t, lt, d):
    interior(ctx, t, ic(DOUBLE_X, HEAD_Y, lerp(2.1, 2.6, ease_io(lt / d)), 760), dbl=dbl_down(t, 1, look=(-0.6, -0.3)),
             dark=0.62)
    post(ctx, t, vignette=1.3)


def watch_closeup(ctx, t, txt='03:17', glow_a=1.0, materialize=1.0, skin=HERO3['skin'], sleeve=HERO3['top']):
    rect(ctx, -500, -500, 2100, 2900, hexc('#0a0b0e'))
    taper(ctx, (-200, 1100), (700, 980), 300, 280, mul(sleeve, 0.8))
    taper(ctx, (650, 990), (1250, 900), 220, 200, mul(skin, 0.9))
    if materialize <= 0:
        return
    ctx.save()
    if materialize < 1:
        r = random.Random(int(t * 30))
        ctx.new_path()
        for i in range(30):
            if r.random() < materialize:
                ctx.rectangle(500, 700 + i * 20, 400, 20)
        ctx.clip()
    rect(ctx, 600, 820, 150, 330, hexc('#141418'))
    rrect(ctx, 540, 860, 270, 250, 50, hexc('#2a2a30'))
    rrect(ctx, 565, 885, 220, 200, 36, hexc('#050506'))
    glow(ctx, 675, 985, 260, RED_LED, 0.35 * glow_a)
    text(ctx, txt, 675, 1010, 74, RED_LED, font='DejaVu Sans Mono Bold')
    ctx.restore()


def s_watch(ctx, t, lt, d):
    t_t = WT('C9', '03:17')
    camera(ctx, 650, 990, lerp(1.0, 1.35, ease_io(lt / d)), t=t)
    watch_closeup(ctx, t, glow_a=0.4 + 0.6 * seg(t, t_t, t_t + 0.3))
    post(ctx, t)
    flash(ctx, 0.25 * math.exp(-max(0, t - t_t) * 6) * (t > t_t), (1, 0.2, 0.2))


def s_finger(ctx, t, lt, d):
    up = ease_io(seg(t, WT('C10', 'поднимает') - 0.1, WT('C10', 'губам', end=True)))
    interior(ctx, t, ic(DOUBLE_X, HEAD_Y + 20, lerp(2.0, 2.5, lt / d), 760),
             dbl=dbl_down(t, 1, look=(-0.8, -0.2), finger_lips=up > 0.5), dark=0.6)
    post(ctx, t, vignette=1.3)


def s_whisper(ctx, t, lt, d):
    interior(ctx, t, ic(DOUBLE_X, HEAD_Y, lerp(3.4, 4.2, ease_io(lt / d)), 720),
             dbl=dbl_down(t, 1, look=(-0.6, -0.1), finger_lips=True, eyes='wide'), dark=0.7)
    post(ctx, t, vignette=1.5)
    scan_tint(ctx, 0.1, (0.05, 0.0, 0.0))


TORSO_H = 150 * 0.92


# =============================================================== 4. the chase
def s_heads_turn(ctx, t, lt, d):
    tt = WT('D1', 'поворачивают') - 0.15
    hu = 1.0 if t > tt else ease_io(seg(t, tt - 0.6, tt))
    sh = shake_env(t, [(tt, 14)], 4)
    camera_args = ic(300, CF + 120, 0.9, 1240)

    def hero(ctx):
        HERO.draw(ctx, -120, CF + 120, 1.05, dict(t=t, facing=1, lit=0.95, eyes='tiny', mouth='o', brows='worried'))
    interior(ctx, t, camera_args, heads_up=hu if t > tt - 0.6 else 0, look=(-1, 0.1),
             dbl=dbl_down(t, 1, look=(-1, 0)), hero_fn=hero, red=0.25 * seg(t, tt, tt + 0.3))
    post(ctx, t)
    glitch(ctx, 0.5 * seg(t, tt, tt + 0.1) * (1 - seg(t, tt + 0.3, tt + 0.6)), t)


def s_step_back(ctx, t, lt, d):
    p = ease_out(seg(lt, 0, d))

    def hero(ctx):
        HERO.draw(ctx, lerp(-120, -420, p), CF + 120, 1.05,
                  dict(walk_pose(-t * 1.2, 0.6), t=t, facing=1, lit=0.95, eyes='tiny', mouth='o', brows='worried',
                       lean=-8, tremble=0.8))
    interior(ctx, t, ic(-150, 1250, 1.4, 800), heads_up=1, look=(-1, 0.1), dbl=dbl_down(t, 1, look=(-1, 0)), hero_fn=hero,
             red=0.25)
    post(ctx, t)


def s_double_rise(ctx, t, lt, d):
    t_up = WT('D3', 'встаёт') - 0.1
    up = ease_out(seg(t, t_up, t_up + 0.25))
    walk = seg(t, WT('D3', 'идти') - 0.1, E('D3') + 0.3)

    def dbl(ctx, x):
        if up < 1:
            DOUBLE.draw(ctx, x, CF, 0.92, double_pose(t, look=(-1, 0), hip_dy=lerp(0, -77, up), sit=SEAT))
    def standing(ctx):
        if up >= 1:
            x = lerp(DOUBLE_X, DOUBLE_X - 700, walk)
            DOUBLE.draw(ctx, x, CF + 60, 1.0, dict(walk_pose(t * 1.0, 0.8), t=t, facing=-1, lit=0.95, watch=True,
                                                   eyes='open', mouth='line', blink=False))
    interior(ctx, t, ic(lerp(700, 300, walk), CF + 60, 1.0, 1240), heads_up=1, look=(-1, 0.1), dbl=dbl, hero_fn=standing,
             red=0.3)
    post(ctx, t)


def s_run(ctx, t, lt, d):
    x = 820 - 900 * lt
    pcam(ctx, x - 150, 0.95, t, shake=8)
    lamps = station(ctx, t, x0=x - 2000, x1=x + 3000, steady=False)
    xh = train_x(t)
    draw_train(ctx, xh, t, doors=1.0, inside=0.7, lit=0.9, door_glow=hexc('#ffc890'))
    HERO.draw(ctx, x, FLOOR, 1.0, dict(run_pose(t * 2.6), t=t, facing=-1, lit=0.9, eyes='wide', mouth='scream',
                                       brows='worried'))
    for cx in (x - 900, x + 400):
        column(ctx, round(cx / 1300) * 1300)
    station_light(ctx, lamps, [(820, 900, 600, 0.6)], 0.78)
    post(ctx, t)


def s_hands(ctx, t, lt, d):
    t_h = WT('D5', 'высовываются') - 0.2
    cl = ease_in(seg(t, S('D5'), t_h + 0.1))
    doors = 1 - 0.8 * cl
    x = 820 - 900 * (t - S('D4'))
    if t < t_h:
        pcam(ctx, 1000, 0.66, t, shake=6)
    else:
        pcam(ctx, 900, 1.15, t, shake=10, floor_y=1500)
    lamps = station(ctx, t, x0=-1500, x1=4500)
    xh = train_x(t)
    draw_train(ctx, xh, t, doors=doors, inside=0.7, lit=0.9, hands=ease_out(seg(t, t_h, t_h + 0.4)))
    if t < t_h:
        HERO.draw(ctx, x, FLOOR, 1.0, dict(run_pose(t * 2.6), t=t, facing=-1, lit=0.9, eyes='wide', mouth='scream'))
    station_light(ctx, lamps, [(1000, 900, 900, 0.5)], 0.78)
    post(ctx, t)
    glitch(ctx, 0.4 * seg(t, t_h, t_h + 0.1) * (1 - seg(t, t_h + 0.4, t_h + 0.8)), t)


def s_stairs_up(ctx, t, lt, d):
    f = clamp(lt / (d - 0.4))
    x, y = stair_point(0.05 + 0.9 * f)
    out = seg(t, WT('D6', 'улицу') - 0.2, E('D6') + 0.2)
    camera(ctx, x + 60, y - 260, 1.1, shake=7, t=t)
    stairs(ctx, t, lit=0.8, exit_light=0.7 + 0.3 * out)
    HERO.draw(ctx, x, y + 6, 1.0, dict(run_pose(t * 2.6), t=t, facing=1, lit=0.9, eyes='wide', mouth='scream',
                                       lean=26))
    d_ = Darkness(ctx, 0.8)
    d_.hole(x, y - 250, 600, 0.8)
    d_.hole(2300, -150, 1100, 0.9)
    d_.apply()
    post(ctx, t)
    flash(ctx, 0.6 * out * (1 - seg(t, E('D6'), E('D6') + 0.3)), (0.7, 0.8, 1.0))


def s_horn(ctx, t, lt, d):
    t_h = WT('D7', 'сигнал') - 0.4
    p = seg(t, S('D7'), t_h)
    sh = shake_env(t, [(t_h, 30)], 2.0) + 2
    camera(ctx, 1800, -60, 0.95, shake=sh, t=t)
    stairs(ctx, t, lit=0.7, exit_light=1.0, flick=False)
    glow(ctx, -500, 1500, 400 + 1600 * p, hexc('#fff3c8'), 0.3 + 0.7 * p)
    HERO.draw(ctx, 2150, -80, 1.0, dict(t=t, facing=-1, lit=0.9, eyes='wide', mouth='o', look=(1, 0.8),
                                        rim=alpha(hexc('#fff3c8'), 0.8 * p)))
    post(ctx, t)
    flash(ctx, 0.5 * seg(t, t_h, t_h + 0.1) * (1 - seg(t, t_h + 0.4, t_h + 1.2)), (1, 0.97, 0.85))


def s_vanish(ctx, t, lt, d):
    t_v = WT('D8', 'исчезает')
    v = ease_in(seg(t, t_v, t_v + 1.6))
    pcam(ctx, 1500, 0.62, t, shake=2, floor_y=1150)
    lamps = station(ctx, t, x0=-1500, x1=4500, steady=True, lit=1 - 0.6 * v)
    xh = train_x(S('B9'))
    draw_train(ctx, xh, t, doors=0.0, inside=0.7 * (1 - v), lit=0.9, dissolve=v, head_lights=1 - v)
    if 0 < v < 1:
        r = random.Random(int(t * 30))
        cut = xh + (4 * (CAR_L + 30)) * (1 - v)
        for i in range(140):
            px = cut + r.uniform(-60, 200)
            py = r.uniform(300, TRACK)
            circle(ctx, px + (t - t_v) * r.uniform(0, 300), py - (t - t_v) * r.uniform(0, 200), r.uniform(2, 6),
                   (0.6, 0.75, 1.0, 0.8 * (1 - v)))
    station_light(ctx, lamps, amount=0.8)
    post(ctx, t)
    glitch(ctx, 0.4 * v * (1 - v) * 4, t, (0.4, 0.6, 1))


# =============================================================== 5. the call
def s_street_breath(ctx, t, lt, d):
    camera(ctx, 700, 1150, lerp(1.2, 1.35, lt / d), t=t)
    lights = street(ctx, t)
    P = dict(t=t, facing=1, lit=0.9, eyes='closed' if (lt % 1.4) < 0.5 else 'open', mouth='scream', brows='worried',
             lean=34 + 4 * math.sin(t * 6), hand_f=(70, 120), hand_b=(60, 130), legs=(8, 20, 14, 24), hip_dy=12)
    HERO.draw(ctx, 820, 1520, 1.0, P)
    d_ = Darkness(ctx, 0.75, color=(0.0, 0.01, 0.03))
    for (x, y, f) in lights:
        d_.hole(x, y + 500, 600, 0.8 * f)
    d_.apply()
    for (x, y, f) in lights:
        glow(ctx, x, y + 20, 200, hexc('#ffe9b0'), 0.4 * f)
    post(ctx, t)


def street_lit(ctx, t, lights, amount=0.75, extra=()):
    d_ = Darkness(ctx, amount, color=(0.0, 0.01, 0.03))
    for (x, y, f) in lights:
        d_.hole(x, y + 500, 600, 0.8 * f)
    for e in extra:
        d_.hole(*e)
    d_.apply()
    for (x, y, f) in lights:
        glow(ctx, x, y + 20, 200, hexc('#ffe9b0'), 0.4 * f)


def s_phone_out(ctx, t, lt, d):
    camera(ctx, 820, 1180, 1.8, t=t)
    lights = street(ctx, t)
    up = ease_out(seg(lt, 0.1, 0.6))
    HERO.draw(ctx, 820, 1520, 1.0, dict(t=t, facing=1, lit=0.9, eyes='open', mouth='scream', brows='worried',
                                        hand_f=(lerp(10, 70, up), lerp(150, 70, up)), phone=True,
                                        look=(0.5, 1.0)))
    street_lit(ctx, t, lights)
    post(ctx, t)


def s_call(ctx, t, lt, d):
    camera(ctx, 540, 960, lerp(1.0, 1.08, lt / d), t=t)
    rect(ctx, -500, -500, 2100, 2900, hexc('#06080e'))
    vib = math.sin(t * 60) * 6 * (int(t * 2) % 2 == 0)
    phone(ctx, 540 + vib, 800, 1.3, lambda c, w, h: screen_call(c, w, h, t, 'incoming'))
    glow(ctx, 540, 960, 700, hexc('#7fa8ff'), 0.2)
    post(ctx, t)


def s_answer(ctx, t, lt, d):
    camera(ctx, 830, 1129 + 200 / 2.6, 2.6, t=t)
    lights = street(ctx, t)
    HERO.draw(ctx, 820, 1520, 1.0, dict(t=t, facing=1, lit=0.95, eyes='wide', mouth='line', brows='worried',
                                        phone_ear=True, phone_glow=True, look=(1, 0)))
    street_lit(ctx, t, lights, extra=[(820, 1080, 300, 0.5)])
    post(ctx, t)


def s_voice(ctx, t, lt, d):
    t_v = S('E6')
    hp = seg(t, t_v, E('E6'))
    z = lerp(3.0, 3.6, ease_io(lt / d))
    camera(ctx, 830, 1129 + 200 / z, z, shake=2 * (t > t_v), t=t)
    lights = street(ctx, t)
    HERO.draw(ctx, 820, 1520, 1.0, dict(t=t, facing=1, lit=0.95, eyes='tiny' if t > t_v else 'wide', mouth='o',
                                        brows='worried', phone_ear=True, phone_glow=True, look=(1, 0),
                                        tremble=0.8 if t > t_v else 0, sweat=hp))
    street_lit(ctx, t, lights, amount=0.8, extra=[(820, 1080, 300, 0.5)])
    post(ctx, t, vignette=1.3)
    if t > t_v:
        scan_tint(ctx, 0.12 * math.sin(t * 20) ** 2, (0.2, 0, 0))


def photo_screen(ctx, w, h, t, meta=0.0):
    screen_bg(ctx, w, h, hexc('#101422'))
    screen_status(ctx, w)
    text(ctx, 'НЕИЗВЕСТНЫЙ', w / 2, 110, 26, (1, 1, 1, 0.9))
    # the photo: you, sitting among the passengers
    ctx.save()
    rrect_path(ctx, 30, 160, w - 60, 420, 18)
    ctx.clip()
    ctx.translate(30, 160)
    ctx.scale((w - 60) / 1000, (w - 60) / 1000)
    ctx.translate(-200, -900)
    carriage(ctx, 1.0, x0=-400, x1=1600, flick=False)
    for i, x in enumerate((0, 160, 320, 640, 800, 960)):
        PASS[i % len(PASS)].draw(ctx, x, CF, 0.92, dict(t=1, facing=0, sit=SEAT, lit=0.8, pale=0.35, head_down=1.0,
                                                         eyes='closed', blink=False))
    HERO.draw(ctx, 480, CF, 0.92, dict(t=1, facing=0, sit=SEAT, lit=0.95, eyes='open', mouth='line', blink=False,
                                        look=(0, 0)))
    ctx.restore()
    rect(ctx, 30, 600, w - 60, 2, (1, 1, 1, 0.15))
    a = meta
    text(ctx, 'Фото · 03:17', 40, 650, 26, (1, 1, 1, 0.9 * a), font='DejaVu Sans', anchor='left')
    text(ctx, 'отправлено 5 секунд назад', 40, 692, 24, (1, 0.4, 0.4, 0.95 * a), font='DejaVu Sans', anchor='left')


def s_hangup(ctx, t, lt, d):
    camera(ctx, 540, 960, 1.05, t=t)
    rect(ctx, -500, -500, 2100, 2900, hexc('#06080e'))
    phone(ctx, 540, 960, 1.45, lambda c, w, h: screen_call(c, w, h, t, 'ended'))
    post(ctx, t)


def s_message(ctx, t, lt, d):
    camera(ctx, 540, 960, 1.05, t=t)
    rect(ctx, -500, -500, 2100, 2900, hexc('#06080e'))
    slide = ease_out(seg(lt, 0.2, 0.6))

    def scr(c, w, h):
        screen_lock(c, w, h, t)
        rrect(c, 20, -120 + 260 * slide, w - 40, 120, 22, (0.95, 0.95, 0.97, 0.95))
        text(c, 'Сообщение · НЕИЗВЕСТНЫЙ', 44, -66 + 260 * slide, 22, hexc('#222222'), font='DejaVu Sans Bold',
             anchor='left')
        text(c, 'Фотография', 44, -30 + 260 * slide, 22, hexc('#444444'), font='DejaVu Sans', anchor='left')
    phone(ctx, 540, 960, 1.45, scr)
    post(ctx, t)


def s_photo(ctx, t, lt, d):
    camera(ctx, 540, lerp(900, 800, ease_io(lt / d)), lerp(1.05, 1.4, ease_io(lt / d)), t=t)
    rect(ctx, -500, -500, 2100, 2900, hexc('#06080e'))
    phone(ctx, 540, 960, 1.45, lambda c, w, h: photo_screen(c, w, h, t, 0.0))
    post(ctx, t)


def s_photo_time(ctx, t, lt, d):
    m = seg(t, WT('F4', 'сделана'), WT('F4', 'сделана') + 0.4)
    camera(ctx, lerp(540, 520, ease_io(lt / d)), lerp(900, 1230, ease_io(lt / d)), lerp(1.3, 1.6, ease_io(lt / d)),
           t=t)
    rect(ctx, -500, -500, 2100, 2900, hexc('#06080e'))
    phone(ctx, 540, 960, 1.45, lambda c, w, h: photo_screen(c, w, h, t, m))
    post(ctx, t)


# =============================================================== 6. impossible ending
def s_look_up(ctx, t, lt, d):
    up = ease_io(seg(lt, 0.2, d))
    camera(ctx, 830, 1060, 2.8, t=t)
    lights = street(ctx, t)
    HERO.draw(ctx, 820, 1520, 1.0, dict(t=t, facing=1, lit=0.95, eyes='open', mouth='line', brows='worried',
                                        head_tilt=lerp(18, -6, up), look=(1, lerp(1, -0.3, up)),
                                        hand_f=(70, 70), phone=True, phone_glow=True))
    street_lit(ctx, t, lights, amount=0.78, extra=[(820, 1100, 300, 0.4)])
    post(ctx, t)


def s_entrance(ctx, t, lt, d):
    camera(ctx, lerp(900, 760, ease_io(lt / d)), 1100, lerp(0.75, 0.85, lt / d), t=t)
    lights = street(ctx, t)
    HERO.draw(ctx, 1150, 1580, 1.05, dict(t=t, facing=-1, lit=0.9, eyes='wide', mouth='o', brows='worried',
                                          hand_f=(40, 110), phone=True))
    street_lit(ctx, t, lights, extra=[(750, 1100, 700, 0.5)])
    post(ctx, t)


def s_confused(ctx, t, lt, d):
    turn = (lt % 1.6) > 0.8
    camera(ctx, 1120, 1180, 1.7, t=t)
    lights = street(ctx, t)
    HERO.draw(ctx, 1150, 1580, 1.05, dict(t=t, facing=1 if turn else -1, lit=0.9, eyes='wide', mouth='o',
                                          brows='worried', hand_f=(40, 110), phone=True, look=(1, 0)))
    street_lit(ctx, t, lights, extra=[(1150, 1300, 400, 0.4)])
    post(ctx, t)


def s_sign(ctx, t, lt, d):
    t_ch = S('G5') - 0.15
    ch = t > t_ch
    gl = seg(t, t_ch - 0.4, t_ch) * (1 - seg(t, t_ch + 0.1, t_ch + 0.6))
    sign = 'ПОСЛЕДНЯЯ СТАНЦИЯ · 03:17' if ch and not (gl > 0.2 and int(t * 20) % 2) else 'МЕТРО'
    camera(ctx, 750, 860 if t < t_ch + 2.5 else 1000, lerp(1.6, 1.25, seg(t, t_ch + 1.5, t_ch + 3.0)),
           shake=6 * gl, t=t)
    lights = street(ctx, t, sign=sign, sign_red=1.0 if ch else 0.0)
    street_lit(ctx, t, lights, amount=0.7, extra=[(750, 810, 700, 0.8 if ch else 0.5)])
    post(ctx, t)
    glitch(ctx, gl, t)


def s_phone_clock(ctx, t, lt, d):
    camera(ctx, 540, 900, lerp(1.1, 1.3, ease_io(lt / d)), t=t)
    rect(ctx, -500, -500, 2100, 2900, hexc('#06080e'))
    red = seg(t, WT('G6', '03:17'), WT('G6', '03:17') + 0.3)
    phone(ctx, 540, 960, 1.45, lambda c, w, h: screen_lock(c, w, h, t, '03:17', red))
    post(ctx, t)


def s_rumble(ctx, t, lt, d):
    sh = 4 + 10 * seg(lt, 0, d)
    camera(ctx, 900, 1150, 0.95, shake=sh, t=t)
    lights = street(ctx, t, sign='ПОСЛЕДНЯЯ СТАНЦИЯ · 03:17', sign_red=1.0, rumble=1.0,
                    entrance_glow=seg(lt, 0.5, d))
    HERO.draw(ctx, 1150, 1580, 1.05, dict(t=t, facing=-1, lit=0.9, eyes='wide', mouth='o', brows='worried',
                                          tremble=1.0, look=(1, 0.6)))
    r = random.Random(int(t * 15))
    for i in range(20):
        circle(ctx, r.uniform(0, 2000), r.uniform(1400, 1700), r.uniform(2, 5), (0.6, 0.6, 0.65, 0.6))
    street_lit(ctx, t, lights, amount=0.72, extra=[(750, 1200, 800, 0.6 * seg(lt, 0.5, d))])
    post(ctx, t)


def s_tilt(ctx, t, lt, d):
    p = ease_io(lt / d)
    camera(ctx, lerp(840, 860, p), lerp(1050, 1370, p), lerp(2.6, 3.0, p), shake=2, t=t)
    lights = street(ctx, t, sign='ПОСЛЕДНЯЯ СТАНЦИЯ · 03:17', sign_red=1.0)
    HERO.draw(ctx, 820, 1520, 1.0, dict(t=t, facing=1, lit=0.95, eyes='wide', mouth='line', brows='worried',
                                        look=(0.6, 1), head_tilt=12, hand_f=(60, 110)))
    street_lit(ctx, t, lights, amount=0.7, extra=[(840, 1300, 500, 0.5)])
    post(ctx, t)


def s_watch_appear(ctx, t, lt, d):
    t_m = WT('H3', 'появились')
    t_t = WT('H4', '03:17')
    m = seg(t, t_m - 0.2, t_m + 0.8)
    camera(ctx, 650, 990, lerp(1.0, 1.3, ease_io(lt / d)), shake=2, t=t)
    watch_closeup(ctx, t, glow_a=0.4 + 0.6 * seg(t, t_t, t_t + 0.3), materialize=m)
    post(ctx, t)
    glitch(ctx, 0.5 * m * (1 - m) * 4, t)
    flash(ctx, 0.3 * math.exp(-max(0, t - t_t) * 5) * (t > t_t), (1, 0.2, 0.2))


def s_realize(ctx, t, lt, d):
    # the street keeps flickering into the carriage
    flick = noise(t * 6, 3) > 0.15 + 0.5 * (1 - lt / d)
    z = lerp(3.2, 2.2, ease_io(lt / d))
    if not flick:
        camera(ctx, 830, 1060, z, t=t)
        lights = street(ctx, t, sign='ПОСЛЕДНЯЯ СТАНЦИЯ · 03:17', sign_red=1.0)
        HERO.draw(ctx, 820, 1520, 1.0, dict(t=t, facing=1, lit=0.95, eyes='tiny', mouth='o', brows='worried',
                                            watch=True, watch_glow=True, tremble=0.8))
        street_lit(ctx, t, lights, amount=0.75)
    else:
        camera(ctx, FREE_X, CF - 330, z * 0.9, t=t)
        carriage(ctx, t, moving=1.0)
        passengers(ctx, t, dbl=filler(t))
        HERO.draw(ctx, FREE_X, CF, 0.92, dict(t=t, facing=0, sit=SEAT, lit=0.95, eyes='tiny', mouth='o',
                                              watch=True, watch_glow=True, blink=False))
        scan_tint(ctx, 0.25)
    post(ctx, t, vignette=1.3)
    glitch(ctx, 0.5 if flick else 0.1, t)


def filler(t):
    def f(ctx, x):
        PASS[1].draw(ctx, x, CF, 0.92, dict(t=t, facing=0, sit=SEAT, lit=0.8, pale=0.35, head_down=1.0, eyes='closed',
                                            blink=False))
    return f


def s_never_left(ctx, t, lt, d):
    p = ease_io(lt / d)
    camera(ctx, FREE_X, lerp(CF - 330, 1080, p), lerp(2.2, 0.9, p), t=t)
    carriage(ctx, t, moving=1.0)
    passengers(ctx, t, dbl=filler(t))
    HERO.draw(ctx, FREE_X, CF, 0.92, dict(t=t, facing=0, sit=SEAT, lit=0.95, eyes='tiny', mouth='o', watch=True,
                                          watch_glow=True, blink=False, brows='worried'))
    d_ = Darkness(ctx, 0.55, color=(0.02, 0.015, 0.0))
    d_.hole(FREE_X, CF - 350, 700, 0.7)
    d_.apply()
    post(ctx, t)


def s_final(ctx, t, lt, d):
    """Over-the-shoulder: you sit opposite your double. He lifts his head, grins and speaks."""
    hu = ease_io(seg(t, t - lt + 0.2, T_DOUBLE - 0.1))
    z = lerp(1.25, 1.75, ease_io(lt / d))
    camera(ctx, 560, HEAD_Y + (960 - 640) / z, z, shake=1.5, t=t)
    carriage(ctx, t, x0=-600, x1=1800, moving=1.0, flick=False)
    for x, i in ((180, 1), (340, 3), (780, 2), (940, 5)):
        PASS[i].draw(ctx, x, CF, 0.92, dict(t=t, facing=0, sit=SEAT, lit=0.75, pale=0.35, head_down=1.0, eyes='closed',
                                            blink=False))
    speaking = T_DOUBLE <= t <= T_DOUBLE + 4.9
    DOUBLE.draw(ctx, 560, CF, 0.92, double_pose(t, head_down=1 - hu, eyes='open' if hu > 0.5 else 'closed',
                                                 mouth='grin' if hu > 0.6 else 'line', look=(0, 0.2),
                                                 watch=True, watch_glow=True))
    # you, from behind, in the foreground
    HERO.draw(ctx, 330, CF + 520, 1.45, dict(t=t, facing=2, lit=0.6))
    d_ = Darkness(ctx, 0.6, color=(0.02, 0.0, 0.0))
    d_.hole(560, CF - 330, 520, 0.8)
    d_.apply()
    if speaking:
        glow(ctx, 560, CF - 330, 300, hexc('#ff3020'), 0.12 + 0.08 * math.sin(t * 30))
    post(ctx, t, vignette=1.3)


def s_end(ctx, t, lt, d):
    rect(ctx, 0, 0, W, H, (0, 0, 0, 1))
    a = seg(lt, 1.0, 1.8)
    text(ctx, 'КОНЕЦ', W / 2, 980, 110, (1, 1, 1, a))
    text(ctx, 'ПОЕЗД 03:17', W / 2, 1060, 36, (1, 0.2, 0.2, a * 0.85), font='DejaVu Sans Mono Bold')
    ctx.identity_matrix()


# =============================================================== shot list
def build_shots():
    L = [(0.0, s_hook), (S('A1') - 0.05, s_timetable), (S('A2') - 0.1, s_cctv), (S('A3') - 0.1, s_missing),
         (S('A4') - 0.1, s_room), (S('B1') - 0.25, s_descend), (S('B2') - 0.1, s_platform),
         (WT('B3', 'а') - 0.1, s_clock), (S('B4') - 0.1, s_wait), (S('B5') - 0.05, s_clock_stop),
         (S('B6') - 0.1, s_silence), (S('B7') - 0.1, s_light), (S('B8') - 0.2, s_arrive), (S('B9') - 0.1, s_doors),
         (S('C1') - 0.1, s_inside), (S('C2') - 0.1, s_heads), (S('C3') - 0.1, s_approach),
         (S('C4') - 0.1, s_head_up), (S('C5') - 0.05, s_freeze), (S('C6') - 0.1, s_same),
         (S('C7') - 0.1, s_compare), (S('C8') - 0.1, s_strange), (S('C9') - 0.1, s_watch),
         (S('C10') - 0.1, s_finger), (S('C11') - 0.05, s_whisper),
         (S('D1') - 0.1, s_heads_turn), (S('D2') - 0.05, s_step_back), (S('D3') - 0.05, s_double_rise),
         (S('D4') - 0.05, s_run), (S('D5') - 0.05, s_hands), (S('D6') - 0.05, s_stairs_up),
         (S('D7') - 0.1, s_horn), (S('D8') - 0.05, s_vanish),
         (S('E1') - 0.1, s_street_breath), (S('E2') - 0.1, s_phone_out), (S('E3') - 0.1, s_call),
         (S('E4') - 0.1, s_answer), (S('E5') - 0.1, s_voice), (S('F1') - 0.1, s_hangup),
         (S('F2') - 0.1, s_message), (S('F3') - 0.1, s_photo), (S('F4') - 0.1, s_photo_time),
         (S('G1') - 0.1, s_look_up), (S('G2') - 0.1, s_entrance), (S('G3') - 0.1, s_confused),
         (S('G4') - 0.1, s_sign), (S('G6') - 0.1, s_phone_clock), (S('H1') - 0.1, s_rumble),
         (S('H2') - 0.1, s_tilt), (S('H3') - 0.1, s_watch_appear), (S('H5') - 0.1, s_realize),
         (S('H6') - 0.1, s_never_left), (E('H6') + 0.5, s_final), (T_BLACK, s_end)]
    out = []
    for i, (t0, fn) in enumerate(L):
        t1 = L[i + 1][0] if i + 1 < len(L) else TOTAL + 1
        out.append([t0, fn, t1])
    return out


SHOTS = build_shots()


def render_frame(ctx, t):
    ctx.save()
    rect(ctx, 0, 0, W, H, (0, 0, 0, 1))
    for (t0, fn, t1) in SHOTS:
        if t0 <= t < t1:
            ctx.save()
            fn(ctx, t, t - t0, t1 - t0)
            ctx.restore()
            break
    ctx.restore()
    ctx.identity_matrix()
    if t < T_BLACK:
        ep1.captions(ctx, t, CAPS, fit=840)
