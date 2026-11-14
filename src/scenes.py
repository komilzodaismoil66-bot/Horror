"""All shots of the film, timed to the narration."""
import math
import random
import cairo
from engine import *
from characters import *
from envs import *
from timeline import T, OFF, DUR, TOTAL, caption_chunks

CAPS = caption_chunks()
RED = hexc('#ff2a2a')
MON_RIM_FIRE = hexc('#ff6a2a')
MON_RIM_RED = hexc('#d0182a')
MON_RIM_COLD = hexc('#8fa6d8')
SW = Stairwell(floors=6, base=1700)


def shake_env(t, events, decay=2.8):
    """events: list of (time, strength)."""
    s = 0.0
    for (te, st) in events:
        if t >= te:
            s += st * math.exp(-(t - te) * decay)
    return s


def zzz(ctx, x, y, t, a):
    for i in range(3):
        ph = (t * 0.5 + i / 3) % 1
        text(ctx, 'Z', x + ph * 60 + i * 6, y - ph * 140, 30 + ph * 26, (0.75, 0.82, 1, a * (1 - ph) * 0.9),
             font='Montserrat Black')


def exclaim(ctx, x, y, p, col=RED, size=120):
    if p <= 0:
        return
    s = back_out(clamp(p * 3))
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    text(ctx, '!', 0, 0, size, col, outline=(0, 0, 0, 1), ow=10)
    ctx.restore()


def sound_rings(ctx, x, y, t, t0, n=3, speed=500, maxr=700, col=(0.85, 0.9, 1.0), w=5, arc=None, gap=0.18):
    for i in range(n):
        lt = t - t0 - i * gap
        if lt < 0:
            continue
        r = 20 + lt * speed
        if r > maxr:
            continue
        a = (1 - r / maxr) * 0.8
        ctx.new_path()
        if arc:
            ctx.arc(x, y, r, arc[0], arc[1])
        else:
            ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.set_line_width(w)
        src(ctx, (col[0], col[1], col[2], a))
        ctx.stroke()


def speech_bubble(ctx, x, y, s, txt, p, tail=(-1, 1)):
    if p <= 0:
        return
    sc = back_out(clamp(p * 4)) * s
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(sc, sc)
    w = text_width(ctx, txt, 54) + 60
    jit = math.sin(p * 60) * 3
    ctx.translate(jit, 0)
    rrect(ctx, -w / 2, -60, w, 90, 26, (0.97, 0.96, 0.92, 1))
    fill_poly(ctx, [(tail[0] * 30, 20), (tail[0] * 90, 80 * tail[1]), (tail[0] * 70, 20)], (0.97, 0.96, 0.92, 1))
    text(ctx, txt, 0, 4, 54, hexc('#c0141e'))
    ctx.restore()


# =============================================================== shots
def s_wake(ctx, t, lt, d):
    t_wake = T(1, 'просыпаешься')
    t_boom = T(1, 'грохота')
    booms = [(0.35, 26), (t_boom, 34)]
    sh = shake_env(t, booms)
    z = lerp(1.55, 1.8, smooth(lt / d))
    camera(ctx, 330, 1060, z, shake=sh, t=t)
    wg = 0.25 + 0.6 * math.exp(-max(0, t - 0.35) * 2) * (t > 0.35) + 0.9 * math.exp(-max(0, t - t_boom) * 1.5) * (
        t > t_boom)
    bedroom(ctx, t, window_glow=clamp(wg), lamp=0.0)
    pillow(ctx)
    sit = ease_out(seg(t, t_boom + 0.15, t_boom + 0.65))
    awake = t >= t_wake
    ctx.save()
    ctx.translate(300, 1150)
    ctx.rotate(math.radians(-90 + 82 * sit))
    look = (0.0, -1.0) if sit < 0.5 else (1.0, 0.0)
    P = dict(t=t, hide_legs=True, lying=False, eyes='closed' if not awake else ('wide' if sit > 0.3 else 'open'),
             mouth='flat' if not awake else ('o' if sit > 0.3 else 'flat'), brows='worried' if awake else 'neutral',
             hand_f=(30, 120), hand_b=(20, 120), look=look, lit=0.8, tremble=0.6 * sit, blink=awake,
             head_tilt=0 if sit > 0.5 else -10)
    HERO.draw(ctx, 0, HIP_H, 1, P)
    ctx.restore()
    bed_blanket(ctx, t, sit)
    if not awake:
        zzz(ctx, 190, 1000, t, 1 - seg(t, 0.3, 0.6))
    if sit > 0:
        exclaim(ctx, 250, 760, seg(t, t_boom + 0.3, t_boom + 1.0), RED, 110)
    d_ = Darkness(ctx, 0.35)
    d_.apply()
    post(ctx, t)
    fade(ctx, 1 - seg(t, 0.0, 0.6))
    flash(ctx, 0.35 * math.exp(-max(0, t - t_boom) * 6) * (t > t_boom), FIRE2)


def s_window(ctx, t, lt, d):
    t0 = T(1, 'ты', 1)
    t_see = T(1, 'видишь')
    t_night = T(1, 'кошмар')
    walk = seg(t, t0 - 0.1, t_see - 0.1)
    x = lerp(380, 560, walk)
    zp = ease_io(seg(t, t_see, t_see + 0.9))
    z = lerp(1.05, 2.6, zp)
    cx = lerp(560, 640, zp)
    cy = lerp(1000, 880, zp)
    sh = 6 * seg(t, t_night, t_night + 0.2) * (1 - seg(t, t_night + 0.5, t_night + 1.2))
    camera(ctx, cx, cy, z, shake=sh, t=t)
    bedroom(ctx, t, window_glow=1.0, lamp=0.0)
    pillow(ctx)
    bed_blanket(ctx, t, 1)
    pose = walk_pose(t * 1.6) if walk < 1 else {}
    fl = 0.7 + 0.3 * noise(t * 8, 2)
    shocked = t >= t_night
    P = dict(pose, t=t, eyes='tiny' if shocked else 'open', mouth='o' if shocked else 'flat',
             brows='worried' if t > t_see else 'neutral', lit=0.85, rim=alpha(FIRE2, 0.55 * fl),
             sweat=seg(t, t_night + 0.2, t_night + 1) if shocked else 0, tremble=1.0 if shocked else 0)
    HERO.draw(ctx, x, 1380, 1, P)
    glow(ctx, 790, 820, 500, FIRE1, 0.25 * fl)
    d_ = Darkness(ctx, 0.3)
    d_.apply()
    post(ctx, t)


def window_frame_overlay(ctx, t):
    ctx.save()
    ctx.identity_matrix()
    c = hexc('#05070e')
    rect(ctx, 0, 0, W, 110, c)
    rect(ctx, 0, 0, 70, H, c)
    rect(ctx, W - 70, 0, 70, H, c)
    rect(ctx, 0, 1640, W, 300, c)
    rect(ctx, 0, 1610, W, 40, hexc('#0d1222'))
    rect(ctx, 0, 820, W, 26, c)
    # hero silhouette (head + shoulders) bottom-left, rim lit by fire
    fl = 0.7 + 0.3 * noise(t * 6, 4)
    HERO.draw(ctx, 230, 2200, 2.4, dict(t=t, facing=1, sil=hexc('#04050a'), rim=alpha(FIRE2, 0.9 * fl),
                                       hand_f=(10, 150), hand_b=(10, 150)))
    ctx.restore()


def s_city(ctx, t, lt, d):
    z = lerp(1.0, 1.12, lt / d)
    camera(ctx, W / 2, H / 2 + 100, z, shake=2, t=t)
    burning_city(ctx, t, base_y=1500, glow_amt=1.0)
    embers(ctx, t, 0, 300, W, 1300, n=50, seed=4)
    window_frame_overlay(ctx, t)
    post(ctx, t)


COLLAPSE_B = dict(x=600, w=260, h=980)


def collapsing_building(ctx, t, tc, ground, lit=1.0):
    b = COLLAPSE_B
    p = ease_in(seg(t, tc, tc + 1.6))
    ang = p * math.radians(-78)
    sink = p * 140
    ctx.save()
    ctx.translate(b['x'], ground + sink)
    ctx.rotate(ang)
    col = mul(hexc('#0b0f1c'), lit)
    rect(ctx, 0, -b['h'], b['w'], b['h'], col)
    r = random.Random(9)
    for cx in range(7):
        for ry in range(24):
            if r.random() < 0.45:
                fl = 0.5 + 0.5 * noise(t * 5 + cx * 3 + ry, 2)
                rect(ctx, 16 + cx * 34, -b['h'] + 24 + ry * 39, 18, 22, alpha(mix(FIRE1, FIRE3, r.random() * 0.5), fl))
    flame(ctx, b['w'] * 0.5, -b['h'] + 4, b['w'] * 0.8, 160, t, 3)
    ctx.restore()
    # chunks breaking off
    if p > 0:
        r = random.Random(4)
        for i in range(14):
            st = tc + 0.2 + r.random() * 0.9
            lt = t - st
            if lt < 0:
                continue
            x0 = b['x'] + r.uniform(0, b['w']) + r.uniform(-1, 1) * 40
            y0 = ground - r.uniform(300, 900)
            x = x0 - lt * r.uniform(60, 220)
            y = y0 + 0.5 * 1800 * lt * lt
            if y > ground + 20:
                continue
            ctx.save()
            ctx.translate(x, y)
            ctx.rotate(lt * r.uniform(-4, 4))
            s = r.uniform(20, 60)
            rect(ctx, -s / 2, -s / 2, s, s * 0.7, mul(hexc('#151a28'), lit))
            ctx.restore()
    # dust cloud
    dp = seg(t, tc + 0.8, tc + 4)
    if dp > 0:
        r = random.Random(12)
        for i in range(16):
            x = b['x'] - 500 * dp * r.random() + r.uniform(-100, 300)
            y = ground - r.uniform(0, 300) * dp
            radial(ctx, x, y, 160 + 240 * dp, hexc('#4a3a36'), 0.55 * (1 - dp * 0.6))


def run_person(ctx, x, y, s, t, style, lit=0.55, phase=0.0, facing=1, scream=True):
    p = run_pose(t * 1.9 + phase)
    HERO_P = Person(style)
    HERO_P.draw(ctx, x, y, s, dict(p, t=t + phase * 3, facing=facing, eyes='wide', brows='worried',
                                   mouth='scream' if scream else 'o', lit=lit, rim=alpha(FIRE2, 0.6)))


def s_street(ctx, t, lt, d):
    tc = T(1, 'рушатся') - 0.25
    tp = T(1, 'люди') - 1.3
    ground = 1300
    sh = shake_env(t, [(tc + 1.5, 22)]) + 2
    pan = lerp(-40, 60, lt / d)
    camera(ctx, W / 2 + pan, 960, 1.0, shake=sh, t=t)
    night_sky(ctx, 1.0, horizon=0.6)
    glow(ctx, 540, 1100, 1000, FIRE1, 0.4)
    SKY_FAR.draw(ctx, ground - 200, t, -200, 0.8, 0.6)
    collapsing_building(ctx, t, tc, ground)
    SKY_MID.draw(ctx, ground - 40, t, -500, 0.9, 0.8)
    for s_ in CITY_SMOKE[:2]:
        s_.y = ground - 600
        s_.draw(ctx, t, 0.6)
    street_ground(ctx, ground, t)
    debris(ctx, ground, seed=2)
    draw_car(ctx, 860, ground + 110, 0.9, t, hexc('#4a3030'), burning=1.0, flip=-1, wreck=1, seed=5)
    # panicking people + dog
    pp = t - tp
    if pp > 0:
        for i, (st, ph, yy, sc) in enumerate(((CROWD_STYLES[0], 0.0, 40, 0.62), (CROWD_STYLES[1], 0.3, 70, 0.66),
                                              (CROWD_STYLES[2], 0.6, 20, 0.58), (CROWD_STYLES[3], 0.15, 90, 0.7))):
            x = -150 + pp * (430 + i * 40) - i * 170
            run_person(ctx, x, ground + yy, sc, t, st, phase=ph)
        draw_dog(ctx, -120 + pp * 520 - 220, ground + 120, 0.9, t, run=True, lit=0.7)
    draw_car(ctx, 260, ground + 300, 1.3, t, hexc('#2f3d5c'), burning=1.0, seed=1)
    embers(ctx, t, -100, 200, W + 200, 1300, n=60, seed=7)
    post(ctx, t)


def height_marker(ctx, x, y0, y1, label, p, col=(1, 1, 1)):
    if p <= 0:
        return
    a = clamp(p * 3)
    yy = lerp(y0, y1, ease_out(clamp(p * 2)))
    ctx.save()
    ctx.set_dash([18, 12])
    line(ctx, (x, y0), (x, yy), 5, (col[0], col[1], col[2], a), cairo.LINE_CAP_BUTT)
    ctx.restore()
    line(ctx, (x - 30, y0), (x + 30, y0), 5, (col[0], col[1], col[2], a))
    if p > 0.5:
        line(ctx, (x - 30, y1), (x + 30, y1), 5, (col[0], col[1], col[2], a))
        sc = back_out(seg(p, 0.5, 0.7))
        ctx.save()
        ctx.translate(x - 50, (y0 + y1) / 2)
        ctx.scale(sc, sc)
        rrect(ctx, -170, -60, 170, 100, 18, (0.75, 0.05, 0.08, 0.92))
        text(ctx, label, -85, 14, 64, (1, 1, 1, 1))
        ctx.restore()


GIANT_SMOKE = [Smoke(x, 1500, seed=40 + i, n=12, size=150, rise=30, life=10, drift=10, col=hexc('#2a2124'),
                     under=hexc('#5a2a1a'), spread=3) for i, x in enumerate((-100, 300, 700, 1100))]


def s_giants(ctx, t, lt, d):
    tm = T(1, 'около')
    camera(ctx, W / 2 + lt * 8, 960, lerp(1.0, 1.06, lt / d), shake=3, t=t)
    vgrad(ctx, 0, -200, W, H + 400, [(0, hexc('#120c12')), (0.5, hexc('#3a1c16')), (0.8, hexc('#6a2e18')),
                                     (1, hexc('#2a1610'))])
    SKY_FAR.draw(ctx, 1250, t, 100, 0.5, 0.4)
    glow(ctx, 540, 1100, 900, FIRE1, 0.3)
    for s_ in GIANT_SMOKE[:2]:
        s_.y = 1350
        s_.draw(ctx, t, 0.8)
    # far monster (hazy)
    mp, dy = monster_walk(t, 0.28, seed=3)
    MONSTER.draw(ctx, 60 + lt * 18, 1250 - 640 * 0.45 + dy * 0.45, 0.45, dict(mp, t=t, body=hexc('#2d2124'),
                                                                rim=alpha(FIRE2, 0.5)), facing=1)
    rect(ctx, -400, 1300, W + 800, 800, hexc('#150e10'))
    for s_ in GIANT_SMOKE[2:]:
        s_.y = 1450
        s_.draw(ctx, t, 0.7)
    draw_car(ctx, 160, 1420, 0.8, t, hexc('#2a2a2a'), burning=0.6, seed=8)
    # near monster
    mp, dy = monster_walk(t, 0.32, seed=1)
    hx = 660 - lt * 22
    GS = 0.74
    MONSTER.draw(ctx, hx, 1368 - 640 * GS + dy * GS, GS, dict(mp, t=t, rim=alpha(FIRE2, 0.95)), facing=-1)
    for s_ in GIANT_SMOKE:
        s_.y = 1700
    GIANT_SMOKE[1].draw(ctx, t + 3, 0.6)
    embers(ctx, t, 0, 400, W, 1200, n=40, seed=8)
    # scale marker: ~5 m
    p = seg(t, tm, tm + 0.9)
    top = 1368 - 640 * GS + dy * GS - GS * 1010
    height_marker(ctx, hx + 300, 1368, top, '5 М', p)
    if p > 0.4:
        # a person for scale
        a = seg(p, 0.4, 0.8)
        HERO.draw(ctx, hx + 400, 1368, 0.78, dict(t=t, facing=-1, sil=(0.02, 0.02, 0.03, a),
                                                  rim=alpha(FIRE2, 0.7 * a)))
    post(ctx, t, tint=(0.25, 0.05, 0.0, 0.06))


def monster_idle(t, seed=0):
    return dict(t=t, head=jerk(t, 1.3, seed) * 14, curl=0.35 + 0.1 * math.sin(t * 2), finger_spread=1.1)


def red_backdrop(ctx, t, cx=540, cy=900):
    rect(ctx, -2000, -2000, 6000, 6000, hexc('#06040a'))
    glow(ctx, cx, cy, 1300, hexc('#7a0a14'), 0.55 + 0.1 * noise(t * 3, 1))
    glow(ctx, cx, cy + 900, 900, FIRE1, 0.25)


def s_anatomy(ctx, t, lt, d):
    t_arms = T(2, 'длинные')
    t_legs = T(2, 'огромные')
    t_head = T(2, 'вытянутая')
    t_eyes = T(2, 'без')
    hip = (540, 1250)
    # camera keyframes
    k = [(OFF[2] - 0.6, (540, 1450, 0.75)), (t_arms, (540, 1450, 0.75)), (t_arms + 0.7, (640, 1650, 1.25)),
         (t_legs, (600, 1650, 1.2)), (t_legs + 0.5, (540, 1870, 1.05)), (t_head - 0.05, (540, 1870, 1.0)),
         (t_head + 0.6, (540, 700, 1.5)), (t_eyes, (540, 690, 1.6)), (t_eyes + 0.6, (540, 720, 2.2)),
         (OFF[2] + 6, (540, 730, 2.3))]
    cx, cy, z = k[0][1]
    for i in range(len(k) - 1):
        (ta, a), (tb, b) = k[i], k[i + 1]
        if ta <= t <= tb:
            f = ease_io(seg(t, ta, tb))
            cx, cy, z = lerp(a[0], b[0], f), lerp(a[1], b[1], f), lerp(a[2], b[2], f)
        elif t > tb:
            cx, cy, z = b
    camera(ctx, cx, cy, z, shake=2, t=t)
    red_backdrop(ctx, t, 540, 1100)
    mp = monster_idle(t, 2)
    mp.update(view='front', hand_b=(250 + math.sin(t * 1.3) * 20, 640), hand_f=(260 + math.sin(t * 1.1) * 20, 650),
              rim=alpha(hexc('#ff3a2a'), 0.9), rim_off=(5, -3), mouth=0.0)
    MONSTER.draw(ctx, hip[0], hip[1], 1.0, mp)
    # highlight pulses on the named body part
    for (tt, x, y, r) in ((t_arms + 0.2, 830, 1830, 260), (t_legs + 0.2, 540, 1870, 360), (t_eyes, 540, 830, 140)):
        a = seg(t, tt, tt + 0.15) * (1 - seg(t, tt + 0.6, tt + 1.4))
        if a > 0:
            glow(ctx, x, y, r, hexc('#ff4040'), 0.25 * a)
    post(ctx, t)


def s_mouth(ctx, t, lt, d):
    t_open = T(2, 'пасть') - 0.1
    t_rows = T(2, 'рядами')
    hip = (540, 1250)
    o = back_out(seg(t, t_open, t_open + 0.55), 1.2)
    zp = ease_io(seg(t, t_rows, t_rows + 1.0))
    head_y = 1250 - 380 - 90 - 150 + 70
    cy = lerp(head_y + 20, head_y + 30, zp)
    z = lerp(3.0, 4.6, zp) + 0.04 * lt
    sh = 10 * seg(t, t_open, t_open + 0.1) * (1 - seg(t, t_open + 0.4, t_open + 1.2)) + 2
    camera(ctx, 540, cy, z, shake=sh, t=t)
    red_backdrop(ctx, t, 540, head_y)
    mp = monster_idle(t, 5)
    mp.update(view='front', mouth=o, drool=1.0, jaw_jitter=0.04 * o, rim=alpha(hexc('#ff3a2a'), 0.9),
              rim_off=(3, -2), head=jerk(t, 2.2, 3) * 6)
    MONSTER.draw(ctx, hip[0], hip[1], 1.0, mp)
    post(ctx, t, tint=(0.3, 0, 0, 0.08 * o))


HEAR_SMOKE = [Smoke(x, 1500, seed=60 + i, n=10, size=140, rise=25, life=10, drift=8, col=hexc('#1c1a22'),
                    under=hexc('#3a1e1a'), spread=3) for i, x in enumerate((100, 600, 1000))]


def s_hearing(ctx, t, lt, d):
    t_hear = T(2, 'слухом') - 0.2
    camera(ctx, 560, 900, 1.15 + 0.03 * lt, shake=2, t=t)
    night_sky(ctx, 0.8, horizon=0.7)
    SKY_MID.draw(ctx, 1500, t, -300, 0.8, 0.7)
    for s_ in HEAR_SMOKE:
        s_.y = 1400
        s_.draw(ctx, t, 0.8)
    turn = ease_out(seg(t, t_hear + 0.55, t_hear + 0.7))
    mp = monster_idle(t, 8)
    mp.update(torso=34, neck=40 + 25 * turn, head=-10 + 40 * turn + jerk(t, 2.0, 2) * 8 * (1 - turn),
              hand_f=(170, 600), hand_b=(120, 580), foot_f=(70, 640), foot_b=(-60, 640), rim=alpha(FIRE2, 0.85),
              mouth=0.12 * turn)
    MONSTER.draw(ctx, 330, 1050, 0.95, mp, facing=1)
    # sound waves coming from the right
    sound_rings(ctx, 1150, 560, t, t_hear, n=4, speed=600, maxr=760, arc=(math.pi * 0.7, math.pi * 1.3), w=8)
    rect(ctx, -400, 1650, W + 800, 600, hexc('#07080d'))
    post(ctx, t)


def s_whisper(ctx, t, lt, d):
    t_wh = T(2, 'шёпот') if False else T(2, 'шопот')
    t_att = T(2, 'внимание')
    camera(ctx, 650, 980, 1.75, shake=1.5, t=t)
    bedroom(ctx, t, window_glow=0.8, lamp=0.0, curtain=0.4)
    # monster head passing behind the window
    hx = lerp(380, 820, ease_io(seg(t, t - lt, t_att)))
    stop = seg(t, t_att, t_att + 0.25)
    ctx.save()
    ctx.rectangle(600, 560, 380, 520)
    ctx.clip()
    mp = monster_idle(t, 4)
    mp.update(torso=20, neck=20, head=-15 + 30 * stop, hand_f=(160, 700), hand_b=(100, 700), rim=alpha(FIRE2, 0.8),
              mouth=0.15 * stop)
    MONSTER.draw(ctx, hx - 120, 1500, 1.1, mp, facing=1 if stop < 0.5 else -1)
    ctx.restore()
    # window frame redraw over the head
    frame = hexc('#0a0e1c')
    rect(ctx, 600 + 190 - 7, 560, 14, 520, frame)
    rect(ctx, 600, 560 + 520 * 0.42, 380, 12, frame)
    # hero pressed to the wall left of window, hands over mouth
    HERO.draw(ctx, 470, 1380, 1.0, dict(t=t, facing=0, hand_mouth=True, eyes='tiny', brows='worried',
                                        look=(1, -0.2), lit=0.75, tremble=1.2, sweat=seg(t, t_att, t_att + 0.8),
                                        rim=alpha(FIRE2, 0.35)))
    if t > t_wh:
        a = seg(t, t_wh, t_wh + 0.2) * (1 - seg(t, t_wh + 1.0, t_wh + 1.5))
        for i, ch in enumerate('ш-ш-ш'):
            text(ctx, ch, 525 + i * 22, 950 - i * 8 + math.sin(t * 10 + i) * 4, 40, (0.8, 0.85, 1, a * 0.85))
    if t > t_att:
        exclaim(ctx, 790, 640, seg(t, t_att + 0.1, t_att + 0.7), RED, 120)
    d_ = Darkness(ctx, 0.45)
    d_.hole(790, 820, 500, 0.6)
    d_.apply()
    post(ctx, t, tint=(0.3, 0.0, 0.0, 0.12 * seg(t, t_att, t_att + 0.3)))


def s_decide(ctx, t, lt, d):
    t_now = T(3, 'немедленно')
    camera(ctx, 380, 980, lerp(1.7, 1.95, lt / d), t=t)
    bedroom(ctx, t, window_glow=0.6, lamp=1.0)
    look_x = math.sin(lt * 3.5) if t < t_now else 0
    HERO.draw(ctx, 380, 1380, 1.0, dict(t=t, facing=0, eyes='open', look=(look_x, 0),
                                        brows='angry' if t > t_now else 'worried',
                                        mouth='flat' if t > t_now else 'frown', lit=0.9,
                                        head_dy=4 * math.sin(seg(t, t_now + 0.3, t_now + 0.8) * math.pi * 2),
                                        rim=alpha(hexc('#ffc46b'), 0.25)))
    d_ = Darkness(ctx, 0.25)
    d_.hole(-170, 1040, 900, 0.8)
    d_.apply()
    post(ctx, t)


def s_pack(ctx, t, lt, d):
    t_bag = T(3, 'рюкзак') - 0.1
    items = [(T(3, 'воду'), draw_bottle, (250, 560), -0.3), (T(3, 'еду'), draw_can, (830, 540), 0.25),
             (T(3, 'аптечку'), draw_medkit, (290, 330), 0.15), (T(3, 'фонарик'), draw_flashlight, (790, 320), -0.5)]
    t_close = T(3, 'фонарик', end=True) + 0.2
    camera(ctx, 540, 900, 1.0 + 0.03 * lt, t=t)
    # wooden floor
    rect(ctx, -200, -200, W + 400, H + 400, hexc('#1a1414'))
    for i in range(-2, 14):
        rect(ctx, -200, i * 150, W + 400, 6, hexc('#120d0d'))
        rect(ctx, (i * 377) % 900 - 100, i * 150, 6, 150, hexc('#120d0d'))
    glow(ctx, 540, 900, 900, hexc('#ffbf66'), 0.45)
    bp = back_out(seg(t, t_bag, t_bag + 0.4))
    bx, by = 540, 1130
    op = 1 - seg(t, t_close, t_close + 0.3)
    if bp > 0:
        ctx.save()
        ctx.translate(bx, by)
        ctx.scale(bp, bp)
        draw_backpack(ctx, 0, 0, 1.45, 1.0, open_=max(0.15, op))
        ctx.restore()
    for (ti, fn, pos, ang) in items:
        p = t - ti
        if p < 0:
            continue
        appear = back_out(clamp(p / 0.25))
        fly = ease_in(seg(p, 0.35, 0.75))
        if fly >= 1:
            continue
        x = lerp(pos[0], bx, fly)
        y = lerp(pos[1], by - 370, fly) - math.sin(fly * math.pi) * 180
        s = appear * (1 - fly * 0.7) * 1.7
        fn(ctx, x, y, s, ang * (1 - fly) + fly * 2, 1.0)
        if fly == 0:
            glow(ctx, x, y, 160, hexc('#ffffff'), 0.12)
    post(ctx, t)


def s_sneak(ctx, t, lt, d):
    k = 2
    y = SW.level(k)
    t_q = T(3, 'тихо')
    dp = ease_out(seg(t, t - lt + 0.1, t - lt + 0.6))
    walk = seg(t, t - lt + 0.5, t - lt + d)
    x = lerp(835, 640, walk)
    camera(ctx, 700, y - 300, 1.35, t=t)
    SW.draw(ctx, t, 1, 4, lit=0.8)
    # opened door (our apartment), warm light spilling
    door(ctx, 760, y, num='12', open_=dp, lit=0.8)
    if dp > 0:
        glow(ctx, 835, y - 150, 300, hexc('#ffc46b'), 0.3 * dp)
    pose = sneak_pose(t * 0.9)
    P = dict(pose, t=t, facing=-1, backpack=True, flashlight=200, eyes='open', brows='worried', mouth='flat',
             look=(0.6, 0.3), lit=0.85)
    pts = HERO.draw(ctx, x, y, 0.95, P)
    d_ = Darkness(ctx, 0.88)
    d_.hole(835, y - 150, 300 * dp, 0.8)
    if 'lens' in pts:
        lx, ly = pts['lens']
        d_.cone(lx, ly, math.radians(pts['lens_ang']) if False else math.radians(180 - 200 + 180), 0.32, 900, 1.0)
        d_.hole(x, y - 250, 260, 0.6)
    d_.apply()
    post(ctx, t)


def s_hear(ctx, t, lt, d):
    t_k = T(4, 'крик')
    k = 2
    y = SW.level(k)
    z = lerp(1.6, 2.6, ease_out(seg(t, t_k, t_k + 0.25)))
    camera(ctx, 650, y - 380, z, shake=8 * seg(t, t_k, t_k + 0.1) * (1 - seg(t, t_k + 1.0, t_k + 2.0)), t=t)
    SW.draw(ctx, t, 1, 4, lit=0.8)
    door(ctx, 760, y, num='12', open_=1.0, lit=0.8)
    frozen = t > t_k
    pose = sneak_pose(0.25) if not frozen else sneak_pose(0.25)
    P = dict(pose, t=t, facing=-1, backpack=True, flashlight=200 + (6 * noise(t * 20, 3) if frozen else 0),
             eyes='tiny' if frozen else 'open', brows='worried', mouth='o' if frozen else 'flat',
             look=(0.8, 0.5) if frozen else (0.6, 0.3), lit=0.85, tremble=1.5 if frozen else 0,
             sweat=seg(t, t_k + 0.3, t_k + 1.5))
    pts = HERO.draw(ctx, 640, y, 0.95, P)
    exclaim(ctx, 600, y - 520, seg(t, t_k, t_k + 0.6), RED, 130)
    sound_rings(ctx, 150, y + 300, t, t_k + 0.4, n=4, speed=420, maxr=600, col=(1, 0.3, 0.3), w=6)
    d_ = Darkness(ctx, 0.88)
    lx, ly = pts['lens']
    d_.cone(lx, ly, math.radians(160), 0.32, 900, 1.0)
    d_.hole(640, y - 250, 260, 0.6)
    d_.apply()
    post(ctx, t, tint=(0.4, 0, 0, 0.25 * math.exp(-max(0, t - t_k) * 3) * (t > t_k)))


# ---- the man on the stairs
MAN = Person(MAN_STYLE)


def man_stage(ctx, t, cam, flick=1.0, hero=True):
    """Common staging: hero on landing level(2), man on mid landing below (mid(1))."""
    k = 2
    y = SW.level(k)
    ym = SW.mid(1)
    camera(ctx, *cam, t=t)
    SW.draw(ctx, t, 0, 4, lit=0.75, window_glow=0.3)
    door(ctx, 760, y, num='12', open_=1.0, lit=0.75)
    pts = None
    if hero:
        P = dict(sneak_pose(0.25), t=t, facing=-1, backpack=True, flashlight=200 - 25, eyes='wide', brows='worried',
                 mouth='o', look=(0.8, 0.8), lit=0.85, tremble=1.0)
        pts = HERO.draw(ctx, 640, y, 0.95, P)
    return y, ym, pts


def s_man(ctx, t, lt, d):
    t_help = T(5, 'зовёт') if False else T(5, 'зовет')
    y, ym, pts = man_stage(ctx, t, (420, SW.mid(1) - 330, 0.95 + 0.04 * lt))
    wave = math.sin(t * 9)
    MAN.draw(ctx, 140, ym, 0.95, dict(t=t, facing=1, hand_f=(40 + 20 * wave, -120), hand_b=(20 - 20 * wave, -110),
                                      eyes='wide', brows='worried', mouth='scream', mouth_open=0.5 + 0.5 * abs(wave),
                                      look=(0.5, -0.8), lit=0.9))
    speech_bubble(ctx, 260, ym - 620, 1.0, 'ПОМОГИТЕ!', seg(t, t_help, t_help + 1))
    d_ = Darkness(ctx, 0.87)
    lx, ly = pts['lens']
    d_.cone(lx, ly, math.radians(200 - 180 + 180 - 25 + 0) if False else math.atan2(ym - 250 - ly, 140 - lx), 0.3,
            1100, 1.0)
    d_.hole(640, y - 250, 240, 0.5)
    d_.apply()
    post(ctx, t)


def man_and_monster(ctx, t, lt, cam, emerge, grab, drag, flick):
    y, ym, pts = man_stage(ctx, t, cam)
    e = ease_io(emerge)
    hip = (lerp(-800, -380, e) - drag * 700, ym - 220 - 40 * e)
    wave = math.sin(t * 9)
    g = ease_out(clamp(grab / 0.35)) if grab > 0 else 0.0
    held = grab > 0.3
    mp = monster_idle(t, 6)
    hand_tgt = (lerp(200, 470, e), lerp(100, -330, e))      # relative to hip: reaching over the man
    if grab > 0:
        hand_tgt = (lerp(hand_tgt[0], 540, g), lerp(hand_tgt[1], -110, g))
    mp.update(torso=lerp(60, 38, e), neck=45, head=-5 + 15 * e, hand_f=hand_tgt, hand_b=(140, 300), foot_f=(150, 320),
              foot_b=(-100, 320), rim=alpha(MON_RIM_COLD, 1.0), rim_off=(8, -4), mouth=0.25 * e + 0.5 * g,
              drool=1.0, curl=lerp(0.35 + 0.2 * e, 1.7, g))
    MS = 0.95
    out = MONSTER.draw(ctx, hip[0], hip[1], MS, mp, facing=1)
    hx, hy = out['hand']
    if not held:
        MAN.draw(ctx, 140, ym, 0.95, dict(t=t, facing=1, hand_f=(40 + 20 * wave, -120), hand_b=(20 - 20 * wave, -110),
                                          eyes='wide', brows='worried', mouth='scream',
                                          mouth_open=0.5 + 0.5 * abs(wave), look=(0.5, -0.8), lit=0.9))
    else:
        kick = math.sin(t * 22)
        MAN.draw(ctx, hx + 40, hy + 250, 0.95, dict(t=t, facing=-1, legs=(25 * kick, 40, -25 * kick, 50),
                                                     hand_f=(70, -60), hand_b=(-50, -40), eyes='tiny',
                                                     brows='worried', mouth='scream', mouth_open=1.0, lit=0.9,
                                                     tremble=2, lean=-15))
        # the fist closes over him: redraw the monster on top, clipped around the hand
        ctx.save()
        ctx.arc(hx, hy + 40, 120, 0, 2 * math.pi)
        ctx.clip()
        MONSTER.draw(ctx, hip[0], hip[1], MS, mp, facing=1)
        ctx.restore()
    d_ = Darkness(ctx, 0.87)
    lx, ly = pts['lens']
    d_.cone(lx, ly, math.atan2(ym - 250 - ly, 140 - lx), 0.3, 1100, flick)
    d_.hole(640, y - 250, 240, 0.5)
    hd = out['head']
    d_.hole(hd[0], hd[1] - 120, 380, 0.55 * e * flick)
    d_.hole(hx, hy, 260, 0.5 * e * flick)
    d_.apply()
    return y, ym


def flicker(t, base=1.0, amount=0.6, seed=0):
    v = noise(t * 18, seed)
    return clamp(base - (amount if v > 0.45 else 0) - 0.15 * abs(noise(t * 40, seed + 1)))


def s_emerge(ctx, t, lt, d):
    t_dark = T(5, 'темноты')
    t_app = T(5, 'появляется')
    em = seg(t, t_dark - 0.2, T(5, 'существо', end=True))
    fl = flicker(t, 1.0, 0.5 * seg(t, t_dark, t_dark + 0.5), 3)
    y, ym = man_and_monster(ctx, t, lt, (230, SW.mid(1) - 420, lerp(1.15, 1.35, lt / d)), em, 0, 0, fl)
    speech_bubble(ctx, 260, ym - 620, 1.0, 'ПОМОГИТЕ!', 1.0 - seg(t, t_app, t_app + 0.3))
    post(ctx, t)


def s_grab(ctx, t, lt, d):
    t_g = T(5, 'хватает')
    t_d = T(5, 'утаскивает')
    grab = clamp((t - t_g + 0.1) / 1.0)
    drag = ease_in(seg(t, t_d, t_d + 0.6))
    sh = shake_env(t, [(t_g, 18), (t_d, 24)])
    fl = flicker(t, 1.0, 0.7, 5)
    y, ym = man_and_monster(ctx, t, lt, (200 - drag * 160, SW.mid(1) - 450, 1.3), 1.0, grab, drag, fl)
    # speed lines while dragged
    if 0 < drag < 1:
        r = random.Random(int(t * 30))
        for i in range(12):
            yy = ym - r.uniform(100, 700)
            x0 = r.uniform(-300, 600)
            line(ctx, (x0, yy), (x0 + 300, yy), 3, (1, 1, 1, 0.25))
    post(ctx, t)
    fade(ctx, 0.0)
    ctx.save()
    ctx.identity_matrix()
    ctx.restore()
    camera_shake_flash = 0.25 * math.exp(-max(0, t - t_g) * 8) * (t > t_g)
    flash(ctx, camera_shake_flash, (1, 0.9, 0.9))


def s_silence(ctx, t, lt, d):
    t_cut = T(5, 'резко')
    y, ym, pts = man_stage(ctx, t, (330, SW.mid(1) - 380, lerp(1.2, 1.55, ease_io(lt / d))))
    # dropped phone with glowing screen
    rrect(ctx, 150, ym - 14, 60, 14, 4, hexc('#101216'))
    glow(ctx, 180, ym - 14, 90, hexc('#8fc0ff'), 0.4 * (0.7 + 0.3 * math.sin(t * 3)))
    rect(ctx, 158, ym - 12, 44, 6, hexc('#a8d0ff'))
    fl = flicker(t, 1.0, 0.6, 9)
    d_ = Darkness(ctx, 0.9)
    lx, ly = pts['lens']
    d_.cone(lx, ly, math.atan2(ym - 250 - ly, 140 - lx) + noise(t * 8, 2) * 0.08, 0.3, 1100, fl)
    d_.hole(640, y - 250, 240, 0.5)
    d_.hole(180, ym - 14, 120, 0.5)
    d_.apply()
    post(ctx, t)


def s_run(ctx, t, lt, d):
    k = 2
    f = seg(t, t - lt + 0.25, t - lt + d + 0.3)
    turn = t - (t - lt) < 0.25
    x, y = SW.flight_point(k, f * 1.0)
    camera(ctx, x + 60, y - 260, 1.3, shake=3, t=t)
    SW.draw(ctx, t, 1, 4, lit=0.75, window_glow=0.3)
    door(ctx, 760, SW.level(k), num='12', open_=1.0, lit=0.75)
    pose = run_pose(t * 2.2) if not turn else sneak_pose(0.25)
    P = dict(pose, t=t, facing=-1, backpack=True, flashlight=(200 - 30 if turn else 160 + 30 * math.sin(t * 9)),
             eyes='wide', brows='worried', mouth='scream', mouth_open=0.5, lit=0.85)
    # climbing: lean into the stairs
    P['lean'] = P.get('lean', 0) + 8
    pts = HERO.draw(ctx, x, y + 6, 0.95, P)
    d_ = Darkness(ctx, 0.87)
    lx, ly = pts['lens']
    ang = math.radians(P['flashlight'])
    d_.cone(lx, ly, math.pi - ang, 0.3, 800, 1.0)
    d_.hole(x, y - 250, 280, 0.6)
    d_.apply()
    post(ctx, t)


def hero_path(f):
    """Path from landing level(2) up to landing level(3): front flight k=2 then back flight k=2."""
    if f < 0.5:
        x, y = SW.flight_point(2, f / 0.5)
        return x, y, -1
    x, y = SW.back_point(2, (f - 0.5) / 0.5)
    return x, y, 1


def s_echo(ctx, t, lt, d):
    t0 = t - lt
    z = lerp(0.42, 0.46, lt / d)
    camera(ctx, 540, SW.level(2) - 120, z, t=t)
    SW.draw(ctx, t, -1, 5, lit=0.7, window_glow=0.4, numbers=True)
    f = clamp(0.35 + lt / d * 0.55)
    x, y, fc = hero_path(f)
    P = dict(run_pose(t * 2.2), t=t, facing=fc, backpack=True, eyes='wide', mouth='scream', lit=1.0)
    HERO.draw(ctx, x, y + 6, 0.95, P)
    # monster waiting at the bottom
    mp = monster_idle(t, 3)
    mp.update(torso=30, rim=alpha(hexc('#ff4a4a'), 0.9), rim_off=(10, -5), hand_f=(150, 600), hand_b=(100, 600))
    ym = SW.level(0)
    MONSTER.draw(ctx, 330, ym - 640 * 0.75, 0.75, mp, facing=1)
    d_ = Darkness(ctx, 0.75)
    d_.hole(x, y - 200, 420, 0.85)
    d_.hole(400, ym - 500, 700, 0.5)
    d_.apply()
    # footstep rings travelling through the whole stairwell
    step_t = 0.3
    n = int(lt / step_t) + 1
    for i in range(n):
        ts = t0 + i * step_t
        if t - ts > 2.2:
            continue
        xs, ys, _ = hero_path(clamp(0.35 + (ts - t0) / d * 0.55))
        sound_rings(ctx, xs, ys, t, ts, n=1, speed=1400, maxr=2300, col=(0.9, 0.95, 1), w=8)
    post(ctx, t)


def head_close(ctx, t, view, mouth, facing=1, rim=MON_RIM_RED, z=3.0, cyoff=0, drool=1.0, jit=0.0, head=0.0,
               cx_off=0.0, blur=0.0):
    hip = (540, 1250)
    if view == 'front':
        hy = 1250 - 380 - 90 - 150 + 40
        camera(ctx, 540 + cx_off, hy + cyoff, z, shake=2 + jit, t=t)
    else:
        camera(ctx, 540 + 300 * facing + cx_off, 600 + cyoff, z, shake=2 + jit, t=t)
    rect(ctx, -2000, -2000, 6000, 6000, hexc('#030306'))
    glow(ctx, 540, 600, 900, hexc('#3a0812'), 0.6)
    mp = monster_idle(t, 1)
    mp.update(view=view, mouth=mouth, drool=drool, rim=alpha(rim, 0.9), rim_off=(4, -2), head=head,
              jaw_jitter=0.03 if mouth > 0.1 else 0)
    if view == 'side':
        mp.update(torso=20, neck=30)
    MONSTER.draw(ctx, hip[0], hip[1], 1.0, mp, facing=facing)


def s_turn(ctx, t, lt, d):
    t_snap = T(6, 'резко') + 0.1
    if t < t_snap:
        head_close(ctx, t, 'side', 0.0, facing=-1, z=1.9, cyoff=170, head=jerk(t, 2, 1) * 10, cx_off=60)
    else:
        p = seg(t, t_snap, t_snap + 0.12)
        head_close(ctx, t, 'front', 0.0, z=lerp(2.2, 2.6, seg(t, t_snap, t_snap + 2)), jit=12 * (1 - p),
                   head=lerp(-25, 0, ease_out(seg(t, t_snap, t_snap + 0.3))))
        if p < 1:
            flash(ctx, 0.5 * (1 - p), (0.6, 0, 0))
    post(ctx, t)


def s_heard(ctx, t, lt, d):
    t_you = T(6, 'тебя')
    o = ease_io(seg(t, t - lt, t_you)) * 0.75
    z = lerp(2.6, 3.0, lt / d) + 1.4 * ease_out(seg(t, t_you, t_you + 0.2))
    head_close(ctx, t, 'front', o, z=z, jit=6 * seg(t, t_you, t_you + 0.1))
    post(ctx, t, tint=(0.35, 0, 0, 0.12 + 0.2 * seg(t, t_you, t_you + 0.2)))


def monster_path(f):
    """Monster climbing: from landing level(0) up through floors to mid(2)."""
    segs = [(SW.flight_point(0, 0), SW.flight_point(0, 1), -1), (SW.back_point(0, 0), SW.back_point(0, 1), 1),
            (SW.flight_point(1, 0), SW.flight_point(1, 1), -1), (SW.back_point(1, 0), SW.back_point(1, 1), 1),
            (SW.flight_point(2, 0), SW.flight_point(2, 1), -1)]
    n = len(segs)
    i = min(n - 1, int(f * n))
    lf = f * n - i
    a, b, fc = segs[i]
    return (lerp(a[0], b[0], lf), lerp(a[1], b[1], lf), fc)


def s_climb(ctx, t, lt, d):
    f = clamp(lt / d * 0.85)
    x, y, fc = monster_path(f)
    camera(ctx, lerp(520, x, 0.5), y - 330, 0.82, shake=7, t=t)
    SW.draw(ctx, t, -1, 5, lit=0.75, window_glow=0.5)
    ph = t * 3.0
    a = math.sin(ph * 2 * math.pi)
    b = math.cos(ph * 2 * math.pi)
    # crawling up the stairs on all fours
    mp = dict(t=t, torso=72 + 6 * a, neck=10, head=-20 + jerk(t, 4, 2) * 10, torso_len=360,
              hand_f=(330 + 120 * a, 160 - 160 + max(0, b) * -60), hand_b=(300 - 120 * a, 40 + max(0, -b) * -60),
              foot_f=(-60 + 120 * a, 330 + max(0, -b) * -50), foot_b=(-160 - 120 * a, 360 + max(0, b) * -50),
              mouth=0.4 + 0.2 * a, drool=1.0, rim=alpha(hexc('#ff4a4a'), 1.0), rim_off=(9, -5), curl=0.8)
    # stairs rise 0.6 per unit: tilt targets accordingly
    for key in ('hand_f', 'hand_b', 'foot_f', 'foot_b'):
        px, py = mp[key]
        mp[key] = (px, py - px * 0.62)
    MONSTER.draw(ctx, x, y - 300, 0.75, mp, facing=fc)
    d_ = Darkness(ctx, 0.62)
    for k in range(0, 5):
        d_.hole(*SW.bulb_pos(k), 240, 0.3)
    d_.hole(x, y - 300, 700, 0.6)
    d_.apply()
    post(ctx, t)


CORNER_X = 1080


def hide_stage(ctx, t, cam, sh=0.0, lit=0.75):
    k = 3
    y = SW.level(k)
    camera(ctx, *cam, shake=sh, t=t)
    SW.draw(ctx, t, 2, 5, lit=lit, window_glow=0.6, numbers=False)
    # right wall (corner)
    rect(ctx, CORNER_X, y - 900, 800, 1000, mul(hexc('#141a2a'), lit))
    rect(ctx, CORNER_X, y - 900, 18, 900, mul(hexc('#0c101b'), lit))
    # big painted floor number
    text(ctx, '4', 960, y - 240, 210, mul(hexc('#6f9aa0'), lit * 1.1), font='DejaVu Sans Bold')
    text(ctx, 'ЭТАЖ', 960, y - 190, 40, mul(hexc('#6f9aa0'), lit * 1.1), font='DejaVu Sans Bold')
    return y


def s_hide(ctx, t, lt, d):
    t_floor = T(7, 'четвертого')
    t_hide = T(7, 'прячешься')
    y = hide_stage(ctx, t, (880, SW.level(3) - 70, 1.55))
    draw_rebar(ctx, (1066, y), (1020, y - 300), 14, 0.8)
    # running in from the back flight, then crouching in the corner
    arrive = seg(t, t - lt, t_hide)
    if t < t_hide:
        if arrive < 0.45:
            x, yy = SW.back_point(2, 0.4 + arrive / 0.45 * 0.6)
        else:
            x, yy = lerp(600, 905, (arrive - 0.45) / 0.55), y
        HERO.draw(ctx, x, yy + 4, 0.95, dict(run_pose(t * 2.2), t=t, facing=1, backpack=True, eyes='wide',
                                             mouth='scream', mouth_open=0.4, brows='worried', lit=0.85))
    else:
        c = ease_out(seg(t, t_hide, t_hide + 0.3))
        P = dict(crouch_pose(), t=t, facing=-1, backpack=True, eyes='tiny', brows='worried', mouth='frown',
                 lit=0.85, tremble=1.5, sweat=seg(t, t_hide, t_hide + 2), look=(-0.5, 0.3))
        P['hip_dy'] = lerp(0, 170, c)
        HERO.draw(ctx, 905, y + 2, 0.95, P)
    pulse = seg(t, t_floor, t_floor + 0.2) * (1 - seg(t, t_floor + 0.6, t_floor + 1.4))
    d_ = Darkness(ctx, 0.82)
    d_.hole(960, y - 300, 420, 0.75)
    d_.hole(960, y - 300, 300, 0.4 * pulse)
    d_.apply()
    if pulse > 0:
        glow(ctx, 960, y - 300, 250, hexc('#9fd8e0'), 0.25 * pulse)
    post(ctx, t)


def rebar_angle(t, t_touch, t_hit):
    """Rebar tips from leaning (~8.7 deg from vertical) to the floor."""
    if t < t_touch:
        return 0.0
    p = seg(t, t_touch, t_hit)
    return ease_in(p) * 1.0


def draw_rebar_state(ctx, t, y, p, bounce=0.0):
    base = (1066, y)
    a0 = math.atan2(-300, -46)
    a1 = math.radians(180 + 2)
    a = lerp(a0, a1, p)
    L = 303
    tip = (base[0] + math.cos(a) * L, base[1] + math.sin(a) * L - bounce)
    draw_rebar(ctx, (base[0], base[1] - bounce * 0.3), tip, 14, 0.8)
    return tip


def s_rebar(ctx, t, lt, d):
    y = hide_stage(ctx, t, (980, SW.level(3) - 110, lerp(2.0, 2.4, ease_io(lt / d))))
    P = dict(crouch_pose(), t=t, facing=-1, backpack=True, eyes='tiny', brows='worried', mouth='frown',
             lit=0.85, tremble=1.5, sweat=1.0, look=(-0.5, 0.3))
    draw_rebar(ctx, (1066, y), (1020, y - 300), 14, 0.9)
    HERO.draw(ctx, 905, y + 2, 0.95, P)
    glow(ctx, 1040, y - 150, 200, hexc('#ffbf80'), 0.12 + 0.05 * math.sin(t * 3))
    d_ = Darkness(ctx, 0.85)
    d_.hole(1000, y - 200, 380, 0.85)
    d_.apply()
    post(ctx, t)


def s_drop(ctx, t, lt, d):
    t_touch = T(7, 'задеваешь')
    t_hit = T(7, 'грохотом') - 0.05
    sh = shake_env(t, [(t_hit, 40)], 2.2)
    zoom = lerp(1.5, 1.7, lt / d) + 0.3 * ease_out(seg(t, t_hit, t_hit + 0.15))
    y = hide_stage(ctx, t, (900, SW.level(3) - 90, zoom), sh=sh)
    shift = seg(t, t_touch - 0.4, t_touch)
    P = dict(crouch_pose(), t=t, facing=-1, backpack=True, eyes='tiny' if t > t_touch else 'wide',
             brows='worried', mouth='scream' if t > t_hit else ('o' if t > t_touch else 'frown'),
             lit=0.85, tremble=1.5, sweat=1.0, look=(0.8, -0.2) if t > t_touch else (-0.6, 0.3))
    P['hip_dx'] = -14 * shift * -1
    P['lean'] = P['lean'] - 10 * shift
    p = seg(t, t_touch, t_hit) ** 2.2
    bounce = 30 * abs(math.sin((t - t_hit) * 14)) * math.exp(-(t - t_hit) * 5) if t > t_hit else 0
    tip = draw_rebar_state(ctx, t, y, p, bounce)
    HERO.draw(ctx, 905, y + 2, 0.95, P)
    if t > t_hit:
        # impact: dust, rings, flash, bang text
        lt2 = t - t_hit
        for i in range(8):
            a = math.pi + i * 0.4
            r = 30 + lt2 * 300
            radial(ctx, tip[0] + 200 + math.cos(a) * r * 0.5, y - 10 - abs(math.sin(a)) * r * 0.3, 70, hexc('#4a4a52'),
                   0.5 * (1 - seg(lt2, 0, 1.5)))
        sound_rings(ctx, 900, y - 10, t, t_hit, n=4, speed=900, maxr=1400, col=(1, 0.95, 0.85), w=10, gap=0.12)
        sc = back_out(seg(lt2, 0, 0.25))
        a = 1 - seg(lt2, 0.8, 1.2)
        if a > 0:
            ctx.save()
            ctx.translate(720, y - 360)
            ctx.rotate(-0.12)
            ctx.scale(sc, sc)
            text(ctx, 'ДЗЫНЬ!', 0, 0, 120, (1, 0.85, 0.2, a), outline=(0.1, 0, 0, a), ow=14)
            ctx.restore()
    d_ = Darkness(ctx, 0.82)
    d_.hole(960, y - 300, 480, 0.75)
    d_.apply()
    post(ctx, t)
    flash(ctx, 0.4 * math.exp(-max(0, t - t_hit) * 7) * (t > t_hit))


def shaft_view(ctx, t, rise, mouth, z=1.0):
    """Looking down the stairwell gap from above."""
    camera(ctx, 540, 960, z, shake=3, t=t)
    rect(ctx, -2000, -2000, 6000, 6000, hexc('#020205'))
    vp = (540, 1050)
    for i in range(9, -1, -1):
        s = 0.78 ** i
        w, h = 900 * s, 1300 * s
        x0, y0 = vp[0] - w / 2, vp[1] - h / 2
        lit = 0.9 * (0.78 ** i)
        # floor slabs between railings
        c = mul(hexc('#2b3246'), lit)
        ctx.new_path()
        ctx.rectangle(x0 - 140 * s, y0 - 140 * s, w + 280 * s, h + 280 * s)
        ctx.rectangle(x0 + w, y0, -w, h)
        src(ctx, c)
        ctx.fill()
        # railing
        ctx.rectangle(x0, y0, w, h)
        ctx.set_line_width(12 * s)
        src(ctx, mul(hexc('#5a3a26'), lit * 1.3))
        ctx.stroke()
        n = 14
        for j in range(n + 1):
            f = j / n
            line(ctx, (x0 + w * f, y0), (x0 + w * f, y0 + 40 * s), 3 * s, mul(hexc('#3c4252'), lit))
            line(ctx, (x0 + w * f, y0 + h), (x0 + w * f, y0 + h - 40 * s), 3 * s, mul(hexc('#3c4252'), lit))
        if i == 0:
            pass
    # monster head at the bottom looking up
    s = lerp(0.35, 0.9, rise)
    ctx.save()
    ctx.translate(vp[0], vp[1] + 120 * (1 - rise))
    ctx.scale(s, s)
    mp = monster_idle(t, 2)
    mp.update(view='front', mouth=mouth, drool=1.0, rim=alpha(MON_RIM_RED, 0.9), head=jerk(t, 3, 2) * 10,
              hand_b=(260, -200), hand_f=(250, -260), lit=0.9)
    MONSTER.draw(ctx, 0, 380 + 90 + 150, 1.0, mp)
    ctx.restore()


def s_knows(ctx, t, lt, d):
    t_k = T(8, 'знает')
    rise = ease_io(seg(t, t - lt, t - lt + d)) * 0.6
    mouth = 0.6 * seg(t, t_k, t_k + 0.4)
    shaft_view(ctx, t, rise, mouth, z=1.0 + 0.1 * lt)
    d_ = Darkness(ctx, 0.5)
    d_.hole(540, 1050, 500, 0.7)
    d_.apply()
    post(ctx, t, tint=(0.3, 0, 0, 0.1))


def s_lunge(ctx, t, lt, d):
    p = ease_in(seg(t, t - lt + 0.1, t - lt + d - 0.1))
    z = lerp(1.6, 6.5, p)
    hy = 1250 - 380 - 90 - 150 + 70
    camera(ctx, 540, hy, z, shake=6 + 30 * p, t=t)
    rect(ctx, -3000, -3000, 8000, 8000, hexc('#030306'))
    glow(ctx, 540, hy, 600, hexc('#5a0a14'), 0.7)
    mp = monster_idle(t, 3)
    mp.update(view='front', mouth=lerp(0.6, 1.1, clamp(p * 2)), drool=1.0, rim=alpha(MON_RIM_RED, 1.0),
              hand_b=(lerp(250, 520, p), lerp(600, -150, p)), hand_f=(lerp(250, 520, p), lerp(600, -200, p)),
              jaw_jitter=0.06, curl=0.9)
    MONSTER.draw(ctx, 540, 1250, 1.0, mp)
    post(ctx, t, tint=(0.4, 0, 0, 0.15 + 0.2 * p))
    flash(ctx, seg(t, t - lt + d - 0.12, t - lt + d), (1, 1, 1))


ESC_SMOKE = [Smoke(x, 1500, seed=80 + i, n=10, size=150, rise=30, life=10, drift=12, col=hexc('#221c22'),
                   under=hexc('#5a2a1a'), spread=3) for i, x in enumerate((-200, 400, 1000, 1600, 2200))]


def s_escape(ctx, t, lt, d):
    escape_street(ctx, t, T(8, 'выскакиваешь') - 0.35, T(8, 'убегаешь'), OFF[8] + DUR[8])


def escape_street(ctx, t, t_out, t_run, t_end, fade_out=True, zoom_end=0.85, ground_fn=None):
    """Hero bursts out of the apartment block door; the monster's arm misses him. Shared by episodes 1 and 2."""
    ground = 1380
    # hero path: door at x=260 -> run right
    run_t = t - t_out
    hx = 300 + max(0, run_t) * 620
    camx = max(540, hx - 120) if t < t_run + 0.6 else (hx - 120)
    zoom = 1.0
    if t > t_run:
        zoom = lerp(1.0, zoom_end, seg(t, t_run, t_end))
    camera(ctx, camx, 1000, zoom, shake=shake_env(t, [(t_out, 18), (t_out + 0.35, 26)]) + 2, t=t)
    night_sky(ctx, 1.0, horizon=0.62, x=camx - 1500, w=3000, y=-600, h=3000)
    glow(ctx, camx + 300, 1100, 1100, FIRE1, 0.45)
    ox = camx * 0.6
    SKY_FAR.draw(ctx, ground - 220, t, ox - 200, 0.8, 0.6)
    SKY_MID.draw(ctx, ground - 60, t, ox * 0.6 + 200, 0.9, 0.8)
    for i, s_ in enumerate(ESC_SMOKE):
        s_.y = ground - 300
        s_.draw(ctx, t, 0.6)
    if ground_fn is None:
        street_ground(ctx, ground, t)
    else:
        ground_fn(ctx, ground, t, camx)
    # apartment block entrance on the left
    rect(ctx, -1400, 0, 1560 + 30, ground, hexc('#141a2a'))
    for r_ in range(6):
        for c_ in range(5):
            on = (r_ * 7 + c_ * 3) % 5 == 0
            rect(ctx, -1300 + c_ * 260, 120 + r_ * 200, 120, 130,
                 hexc('#ff8a3a', 0.6 + 0.3 * noise(t * 4 + r_ + c_, 2)) if on else hexc('#0a0e18'))
    rect(ctx, 160, 0, 30, ground, hexc('#0b0f1a'))
    rect(ctx, 60, ground - 420, 380, 30, hexc('#1e2436'))     # canopy
    # door bursting open
    op = ease_out(seg(t, t_out - 0.05, t_out + 0.15))
    rect(ctx, 200, ground - 380, 190, 380, hexc('#000000'))
    ctx.save()
    ctx.translate(390, ground - 380)
    ctx.scale(1 - op * 1.6, 1)
    rect(ctx, -190, 0, 190, 380, hexc('#3a4458'))
    rect(ctx, -170, 30, 150, 140, hexc('#2c3446'))
    circle(ctx, -160, 200, 9, hexc('#9aa0aa'))
    ctx.restore()
    # monster arm smashing out of the doorway, claws snapping just behind the hero
    ar = seg(t, t_out + 0.25, t_out + 0.55)
    back = seg(t, t_out + 1.2, t_out + 2.4)
    if ar > 0 and back < 1:
        ctx.save()
        ctx.rectangle(200, ground - 380, 3000, 380)
        ctx.clip()
        reach = ease_out(ar) * (1 - ease_in(back))
        mp = dict(t=t, torso=80, neck=10, head=0, hand_f=(lerp(200, 760, reach), 150),
                  hand_b=(100, 400), foot_f=(0, 640), foot_b=(-100, 640), rim=alpha(MON_RIM_FIRE, 0.8),
                  curl=lerp(0.2, 1.4, seg(t, t_out + 0.5, t_out + 0.75)), mouth=0.5)
        MONSTER.draw(ctx, -330, ground - 520, 0.9, mp, facing=1)
        ctx.restore()
    # hero
    if run_t > -0.05:
        HERO.draw(ctx, hx, ground + 30, 0.9, dict(run_pose(t * 2.4), t=t, facing=1, backpack=True, eyes='wide',
                                                  brows='worried', mouth='scream', mouth_open=0.5, lit=0.9,
                                                  rim=alpha(FIRE2, 0.4)))
    # foreground debris & a burning car
    draw_car(ctx, 1900, ground + 260, 1.2, t, hexc('#3a3030'), burning=1.0, seed=3)
    embers(ctx, t, camx - 600, 200, 1200, 1300, n=50, seed=11)
    post(ctx, t)
    if fade_out:
        fade(ctx, seg(t, t_end + 0.3, t_end + 1.2))


def s_outro(ctx, t, lt, d):
    rect(ctx, 0, 0, W, H, hexc('#000000'))
    a = seg(lt, 0.2, 0.9)
    glow(ctx, 540, 900, 700, hexc('#5a0a14'), 0.5 * a)
    # silhouette of a creature in the background
    mp = monster_idle(t, 3)
    mp.update(view='front', mouth=0.0, rim=alpha(MON_RIM_RED, 0.7 * a), lit=0.6, hand_b=(250, 640),
              hand_f=(250, 640))
    ctx.save()
    MONSTER.draw(ctx, 540, 1150, 0.7, mp)
    ctx.restore()
    rect(ctx, 0, 1300, W, 700, (0, 0, 0, 0.6))
    text(ctx, 'ЧАСТЬ 1', 540, 1150, 130, (1, 1, 1, a), outline=(0, 0, 0, a), ow=10)
    b = seg(lt, 0.9, 1.5)
    text(ctx, 'ПРОДОЛЖЕНИЕ СЛЕДУЕТ...', 540, 1260, 54, (1, 0.25, 0.25, b))
    post(ctx, t)
    fade(ctx, seg(lt, d - 0.5, d))


# =============================================================== shot list
def build_shots():
    S = []

    def add(t0, fn):
        S.append([t0, fn])

    add(0.0, s_wake)
    add(T(1, 'ты', 1) - 0.1, s_window)
    add(T(1, 'весь') - 0.15, s_city)
    add(T(1, 'машины') - 0.15, s_street)
    add(T(1, 'но') - 0.1, s_giants)
    add(OFF[2] - 0.35, s_anatomy)
    add(T(2, 'вместо') - 0.2, s_mouth)
    add(T(2, 'они') - 0.2, s_hearing)
    add(T(2, 'даже') - 0.15, s_whisper)
    add(OFF[3] - 0.3, s_decide)
    add(T(3, 'собираешь') - 0.15, s_pack)
    add(T(3, 'затем') - 0.15, s_sneak)
    add(OFF[4] - 0.2, s_hear)
    add(OFF[5] - 0.2, s_man)
    add(T(5, 'в') - 0.05, s_emerge)
    add(T(5, 'оно') - 0.1, s_grab)
    add(T(5, 'крик') - 0.1, s_silence)
    add(OFF[6] - 0.25, s_run)
    add(T(6, 'твои') - 0.1, s_echo)
    add(T(6, 'монстр') - 0.1, s_turn)
    add(T(6, 'он') - 0.1, s_heard)
    add(OFF[7] - 0.3, s_climb)
    add(T(7, 'ты') - 0.15, s_hide)
    add(T(7, 'рядом') - 0.1, s_rebar)
    add(T(7, 'ты', 1) - 0.1, s_drop)
    add(OFF[8] - 0.3, s_knows)
    add(T(8, 'он') - 0.1, s_lunge)
    add(T(8, 'ты', 1) - 0.05, s_escape)
    add(OFF[8] + DUR[8] + 1.2, s_outro)
    for i in range(len(S)):
        S[i].append(S[i + 1][0] if i + 1 < len(S) else TOTAL)
    return S


SHOTS = build_shots()


# =============================================================== overlays
def hud(ctx, t):
    if t > OFF[8] + DUR[8] + 1.0:
        return
    m = 17 + int(t / 14)
    s = f'НОЧЬ — 03:{m:02d}'
    ctx.save()
    ctx.identity_matrix()
    w = text_width(ctx, s, 34, 'DejaVu Sans Mono Bold') + 70
    rrect(ctx, W / 2 - w / 2, 120, w, 62, 10, (0.03, 0.02, 0.04, 0.75))
    if int(t * 1.5) % 2 == 0:
        circle(ctx, W / 2 - w / 2 + 30, 151, 9, (1, 0.15, 0.15, 1))
    text(ctx, s, W / 2 + 14, 163, 34, (1, 0.25, 0.25, 1), font='DejaVu Sans Mono Bold')
    ctx.restore()


def captions(ctx, t, caps=None, fit=None):
    ctx.save()
    ctx.identity_matrix()
    for c in (CAPS if caps is None else caps):
        if not (c['start'] <= t < c['end']):
            continue
        lt = t - c['start']
        pop = back_out(clamp(lt / 0.16), 2.2)
        size = 92
        ws = [w for w in c['words']]
        sp = 40
        widths = [text_width(ctx, w[0], size) for w in ws]
        if fit is not None and max(widths) > fit:      # a single very long word: shrink to fit the screen
            size = size * fit / max(widths)
            widths = [text_width(ctx, w[0], size) for w in ws]
        # wrap into lines no wider than 940
        lines_, cur, cw = [], [], 0
        for i, w in enumerate(ws):
            ww = widths[i]
            if cur and cw + sp + ww > 940:
                lines_.append(cur)
                cur, cw = [], 0
            cur.append(i)
            cw += (sp if cw else 0) + ww
        if cur:
            lines_.append(cur)
        y0 = 1420 - (len(lines_) - 1) * 55
        ctx.translate(W / 2, y0)
        ctx.scale(pop, pop)
        ctx.translate(-W / 2, -y0)
        for li, ln in enumerate(lines_):
            tw = sum(widths[i] for i in ln) + sp * (len(ln) - 1)
            x = W / 2 - tw / 2
            y = y0 + li * 110
            for i in ln:
                w, a, b, hot = ws[i]
                active = a - 0.03 <= t
                cur_w = active and (t < b + 0.12 or i == len(ws) - 1)
                col = (1, 1, 1, 1)
                if active:
                    col = (1, 0.18, 0.18, 1) if hot else (1, 0.84, 0.16, 1)
                if not active:
                    col = (1, 1, 1, 1)
                ctx.save()
                cx = x + widths[i] / 2
                sc = 1.05 if cur_w else 1.0
                ctx.translate(cx, y - 30)
                ctx.scale(sc, sc)
                ctx.translate(-cx, -(y - 30))
                # shadow
                text(ctx, w, x + 4, y + 8, size, (0, 0, 0, 0.6), anchor='left', outline=(0, 0, 0, 0.6), ow=16)
                if cur_w:
                    ctx.save()
                    text_path(ctx, w, x, y, size, anchor='left')
                    src(ctx, (col[0], col[1] * 0.8, 0.0, 0.35))
                    ctx.set_line_width(34)
                    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
                    ctx.stroke()
                    ctx.restore()
                text(ctx, w, x, y, size, col, anchor='left', outline=(0.02, 0.02, 0.04, 1), ow=14)
                ctx.restore()
                x += widths[i] + sp
    ctx.restore()


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
    hud(ctx, t)
    captions(ctx, t)
