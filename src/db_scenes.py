"""«Крик»: every shout is twice as loud. 11 stages, 20 → 20 480 ДБ. Only the author's voice is used."""
import math
import random
import subprocess
import numpy as np
import cairo
from engine import *
from chars3 import Toon, HERO3
from db_envs import *
from db_timeline import STAGES, STAGE, SHOUT_AT, TOTAL, ROOT, VOICE, SPD, INTER, stage_at, fmt

STYLE = dict(HERO3, hair=hexc('#4a3226'), hair_d=hexc('#352318'), top=hexc('#1d1f26'), top_d=hexc('#15161b'),
             pants=hexc('#16171c'), shoe=hexc('#f2f2f0'), skin=hexc('#e3b58e'), skin_d=hexc('#c4946c'),
             brow=hexc('#352318'), cap=hexc('#c8302a'), cap_logo=hexc('#f4f4f4'), chain=True, pocket=True)
HERO = Toon(STYLE)
HX, HY, HS = 540, 1745, 1.55


def _voice_env():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', VOICE, '-f', 's16le', '-ac', '1', '-ar', '8000', '-'],
                         capture_output=True).stdout
    x = np.abs(np.frombuffer(raw, np.int16).astype(np.float32) / 32768)
    win = 400
    e = np.convolve(x, np.ones(win) / win, 'same')
    e = e / (e.max() + 1e-9)
    return e, len(x) / 8000


ENV, VDUR = _voice_env()


def voice_open(lt):
    """Mouth opening from the real recording's envelope (lt = time inside the stage)."""
    v = lt - SHOUT_AT
    if v < 0 or v >= VDUR:
        return 0.0
    return float(clamp(ENV[int(v * 8000)] * 1.6))


def shouting(lt):
    return SHOUT_AT - 0.05 <= lt <= SHOUT_AT + VDUR + 0.05


# ---------------------------------------------------------------- hero
def hero(ctx, k, lt, t, x=HX, y=HY, s=HS, lit=1.0):
    o = voice_open(lt)
    P = dict(t=t, facing=0, lit=lit, blink=True, eyes='open', mouth='line', brows='neutral')
    if lt < SHOUT_AT:                     # inhale
        P.update(head_dy=-4 * seg(lt, 0, SHOUT_AT), brows='angry', eyes='open', mouth='line')
    elif shouting(lt):
        P.update(eyes='squeeze', mouth='shout', mouth_open=max(0.35, o), brows='angry',
                 hand_f=(46, 118), hand_b=(46, 118), tremble=0.4 + 0.25 * k, head_dy=-6)
    else:
        if k >= 5:
            P.update(ears=True, eyes='squeeze', mouth='frown', brows='worried', tremble=0.3 + 0.1 * k)
        elif k >= 3:
            P.update(eyes='wide', mouth='o', brows='worried', look=(math.sin(t * 2), -0.3))
        else:
            P.update(eyes='open', mouth='smile', look=(math.sin(t * 1.5) * 0.8, -0.2))
    return HERO.draw(ctx, x, y, s, P)


def mouth_point(x=HX, y=HY, s=HS):
    return (x, y - (195 + 150 + 46) * s + 0.5 * 54 * s)


def shout_rings(ctx, k, lt, origin, scale=1.0):
    st = (lt - SHOUT_AT) * 1.25
    if st < 0:
        return
    n = 3 + k // 2
    for i in range(n):
        tt = st - i * 0.16
        if tt < 0 or tt > 2.2:
            continue
        r = 40 + tt * (500 + 260 * k) * scale
        a = (1 - tt / 2.2) * (0.25 + 0.06 * k)
        shock_ring(ctx, origin[0], origin[1], r, 4 + 2.2 * k, min(0.9, a))


def shake_amount(k, lt):
    st = (lt - SHOUT_AT) * SPD
    base = [0, 0, 1, 3, 7, 10, 16, 22, 28, 34, 40][k]
    if st < 0:
        return base * 0.15
    return base * (0.4 + 0.6 * math.exp(-st * 0.6))


# ---------------------------------------------------------------- HUD
def hud(ctx, k, lt):
    val = STAGES[k][0]
    prev = STAGES[k - 1][0] if k > 0 else 0
    cnt = int(lerp(prev, val, ease_out(seg(lt, 0.05, 0.5))))
    pop = 1 + 0.25 * math.exp(-lt * 8)
    x0 = 60
    ctx.save()
    ctx.identity_matrix()
    text(ctx, f'КРИК №{k + 1}', x0, 135, 40, (1, 1, 1, 0.95), anchor='left', outline=(0, 0, 0, 0.6), ow=8)
    ctx.save()
    ctx.translate(x0, 300)
    ctx.scale(pop, pop)
    size = 170 if val < 10000 else 150
    text(ctx, f'{fmt(cnt)} ДБ', 0, 0, size, hexc('#ffd21f'), anchor='left', outline=(0.08, 0.06, 0.0, 1), ow=16)
    ctx.restore()
    tag = 'КАЖДЫЙ РАЗ В 2 РАЗА ГРОМЧЕ'
    tw = text_width(ctx, tag, 34) + 40
    rect(ctx, x0, 340, tw, 58, hexc('#e3262a'))
    text(ctx, tag, x0 + 20, 381, 34, (1, 1, 1, 1), anchor='left')
    # what happens (appears with the shout)
    cap = STAGES[k][1]
    a = seg(lt, SHOUT_AT + 0.2, SHOUT_AT + 0.45)
    if a > 0:
        lines_, cur = [], ''
        for w in cap.split():
            test = (cur + ' ' + w).strip()
            if text_width(ctx, test, 60) > 960 and cur:
                lines_.append(cur)
                cur = w
            else:
                cur = test
        lines_.append(cur)
        sc = back_out(seg(lt, SHOUT_AT + 0.2, SHOUT_AT + 0.5), 1.5)
        ctx.save()
        ctx.translate(x0, 470)
        ctx.scale(sc, sc)
        for i, ln in enumerate(lines_):
            text(ctx, ln, 0, i * 72, 60, (1, 1, 1, a), anchor='left', outline=(0, 0, 0, a), ow=12)
        if k >= 8:
            text(ctx, SPACE_NOTE, 0, len(lines_) * 72 + 6, 38, (0.75, 0.85, 1, a), anchor='left',
                 outline=(0, 0, 0, a), ow=8)
        ctx.restore()
    ctx.restore()


# ---------------------------------------------------------------- the prehistoric world (stages 1-8)
def world(ctx, k, lt, t):
    after = lt > SHOUT_AT
    st = max(0.0, lt - SHOUT_AT) * SPD
    z = 1.0 + 0.012 * k + 0.02 * ease_out(seg(st, 0, 1.5))
    camera(ctx, 540, 1100, z, shake=shake_amount(k, lt), t=t)
    heat = ease_io(seg(st, 0.2, 5.0)) if k == 7 else 0.0
    sky(ctx, t, heat)
    clouds(ctx, t, heat, blow=ease_out(seg(st, 0, 4)) * 0.4 if k >= 6 else 0)
    collapse = 1.0 if k > 6 else (ease_io(seg(st, 0.1, 5.5)) if k == 6 else 0.0)
    mountains(ctx, t, collapse, heat)
    evap = ease_io(seg(st, 1.5, 6.5)) if k == 7 else 0.0
    sea(ctx, t, evap, heat)
    # sauropod behind the trees (stage 6)
    if k == 5:
        sauropod(ctx, lerp(-500, 1500, seg(lt, 0.8, STAGE)), GROUND + 20, 0.42, t)
    rustle = [0.4, 1.2, 1.4, 2.0, 2.0, 2.0, 2.0, 2.0][k] * (1 if after else 0.3)
    shake = [0, 0, 0.2, 1.0, 0.7, 0.7, 0.9, 0.6][k] * (math.exp(-st * 0.3) if after else 0.0)
    flatten = ease_out(seg(st, 0, 1.2)) * 0.5 if k >= 6 else 0.0
    burn = ease_io(seg(st, 1.0, 5.5)) if k == 7 else 0.0
    jungle(ctx, t, rustle=rustle, shake=shake, flatten=flatten, burn=burn)
    if k == 2:
        birds(ctx, t, st - 0.15)
    if k in (1, 3):
        falling_leaves(ctx, t, 0.5 if k == 1 and after else (1.5 if after else 0))
    sway = [1.5, 0.8, 1, 2, 2, 2, 3, 2][k] * (1 if after else 0.2)
    cracks = 1.0 if k > 4 else (ease_out(seg(st, 0.0, 3.5)) if k == 4 else 0.0)
    lava = ease_io(seg(st, 0.5, 4.5)) if k == 7 else 0.0
    field(ctx, t, sway=sway, cracks=cracks, heat=heat, lava=lava)
    # panicking dinosaurs (stage 6)
    if k == 5 and after:
        p = st
        pterosaur(ctx, 200 + p * 260, 820 - p * 70, 0.7, t, seed=1)
        pterosaur(ctx, 420 + p * 300, 760 - p * 90, 0.55, t, seed=2)
        pterosaur(ctx, -100 + p * 280, 900 - p * 60, 0.6, t, seed=3)
        triceratops(ctx, -400 + p * 330, GROUND + 130, 0.62, t, seed=1)
        raptor(ctx, -300 + p * 430, GROUND + 160, 0.8, t, seed=1)
        raptor(ctx, -520 + p * 440, GROUND + 150, 0.72, t, seed=2)
        for i in range(12):
            radial(ctx, -500 + p * 360 + i * 70, GROUND + 300, 120, hexc('#c8b58a'), 0.25)
        trex(ctx, -650 + p * 380, GROUND + 330, 0.95, t, run=1.0, jaw=0.8)
        triceratops(ctx, -1100 + p * 360, GROUND + 330, 0.7, t, seed=3)
        raptor(ctx, -200 + p * 470, GROUND + 300, 0.85, t, seed=3)
    if k == 4 and after:
        r = random.Random(int(t * 10))
        for i in range(10):
            radial(ctx, r.uniform(0, 1080), r.uniform(1300, 1900), 80, hexc('#b8a078'), 0.3 * math.exp(-st * 0.6))
    hero(ctx, k, lt, t, lit=1 - 0.15 * heat)
    shout_rings(ctx, k, lt, mouth_point())
    if heat > 0:
        embers_heat(ctx, t, heat)


def embers_heat(ctx, t, a):
    r = random.Random(4)
    for i in range(int(80 * a)):
        ph = (t * r.uniform(0.2, 0.5) + r.random()) % 1
        x = r.uniform(-50, 1130) + math.sin(t + i) * 30
        y = 1900 - ph * 1500
        circle(ctx, x, y, r.uniform(2, 5), alpha(hexc('#ffa030'), (1 - ph) * a))


# ---------------------------------------------------------------- space (stages 9-11)
def space_hero(ctx, k, lt, t):
    """After the Earth is gone the hero simply floats in open space."""
    bob = math.sin(t * 1.3) * 18
    ctx.save()
    ctx.translate(540, 1560 + bob)
    ctx.rotate(math.sin(t * 0.7) * 0.08)
    hero(ctx, k, lt, t, x=0, y=0, s=1.25)
    ctx.restore()
    return (540, 1560 + bob)


SPACE_NOTE = '*если бы в космосе был звук'
EARTH_C, EARTH_R = (540, 1080), 430
YOU_ON_EARTH = (540, 1080 - 430 * 0.62)          # your spot on the surface (far too small to see from here)


def stage_planet(ctx, k, lt, t):
    st = max(0.0, lt - SHOUT_AT) * SPD
    camera(ctx, 540, 1000, 1.0 + 0.02 * seg(st, 0, 6), shake=shake_amount(k, lt), t=t)
    space_bg(ctx, t)
    crack = ease_out(seg(st, 0.2, 2.8))
    split = ease_in(seg(st, 2.6, 7.6))
    earth(ctx, EARTH_C[0], EARTH_C[1], EARTH_R, t, heat=1.0, crack=crack, split=split)
    if split > 0:
        r = random.Random(11)
        for i in range(90):
            a = r.uniform(0, 2 * math.pi)
            d = EARTH_R + split * r.uniform(100, 800)
            circle(ctx, EARTH_C[0] + math.cos(a) * d, EARTH_C[1] + math.sin(a) * d, r.uniform(3, 10), hexc('#ff9a40'))
    # the scream comes from a tiny point on the surface: you
    if split < 0.3:
        glow(ctx, YOU_ON_EARTH[0], YOU_ON_EARTH[1], 60, hexc('#ffffff'), 0.6 * voice_open(lt) + 0.15)
    shout_rings(ctx, k, lt, YOU_ON_EARTH, 1.3)


PLANETS = [(160, 760, 70, '#c8502a', False, False), (880, 650, 120, '#d8a868', False, True),
           (300, 1180, 90, '#e0c890', True, False), (900, 1150, 50, '#6a8ab8', False, False)]


def stage_wave(ctx, k, lt, t):
    st = max(0.0, lt - SHOUT_AT) * SPD
    camera(ctx, 540, 1000, 1.0, shake=shake_amount(k, lt), t=t)
    space_bg(ctx, t, streak=ease_in(seg(st, 0.3, 3.0)) * 2.5, cx=540, cy=1200)
    glow(ctx, -200, 300, 700, hexc('#ffd070'), 0.7)
    circle(ctx, -200, 300, 260, hexc('#fff0b0'))
    R = st * 330
    ox, oy = 540, 1140
    for (x, y, r, c, ring, bands) in PLANETS:
        d = math.hypot(x - ox, y - oy)
        hit = clamp((R - d) / 300)
        if hit < 1:
            ctx.save()
            ctx.translate(x, y)
            ctx.translate(-x, -y)
            planet(ctx, x + (x - ox) / d * hit * 200, y + (y - oy) / d * hit * 200, r, hexc(c), ring, bands)
            ctx.restore()
        if hit > 0:
            rr = random.Random(int(x))
            for i in range(40):
                a = rr.uniform(0, 2 * math.pi)
                dd = hit * rr.uniform(40, 360)
                circle(ctx, x + math.cos(a) * dd + (x - ox) / d * hit * 300,
                       y + math.sin(a) * dd + (y - oy) / d * hit * 300, rr.uniform(3, 9),
                       alpha(hexc(c), 1 - hit * 0.6))
            glow(ctx, x, y, r * 3, hexc('#ffffff'), 0.6 * (1 - abs(hit - 0.3)))
    # the energy wave
    for i in range(3):
        rr_ = R - i * 90
        if rr_ > 0:
            glow(ctx, ox, oy, rr_ + 120, hexc('#8fd0ff'), 0.12)
            shock_ring(ctx, ox, oy, rr_, 40 - i * 10, 0.85 - i * 0.25, (0.75, 0.9, 1.0))
    p = space_hero(ctx, k, lt, t)
    shout_rings(ctx, k, lt, (p[0], p[1] - 420), 1.4)


def stage_galaxy(ctx, k, lt, t):
    st = max(0.0, lt - SHOUT_AT) * SPD
    camera(ctx, 540, 1000, 1.0 - 0.1 * seg(st, 0, 6), shake=shake_amount(k, lt), t=t)
    space_bg(ctx, t, streak=ease_in(seg(st, 0.2, 2.5)) * 3)
    blast = ease_in(seg(st, 1.2, 5.6))
    galaxy(ctx, 540, 760, t, blast=blast, rotation=t * 0.05)
    R = ease_in(seg(st, 0.3, 5.8)) * 2600
    if R > 0:
        glow(ctx, 540, 1140, R + 200, hexc('#ffffff'), 0.5)
        glow(ctx, 540, 1140, R * 0.6 + 100, hexc('#ffe8a0'), 0.7)
        shock_ring(ctx, 540, 1140, R, 60, 0.9, (1, 0.95, 0.8))
    p = space_hero(ctx, k, lt, t)
    shout_rings(ctx, k, lt, (p[0], p[1] - 420), 1.6)


# ---------------------------------------------------------------- frame
def no_sound_card(ctx, lt):
    """'In space there is no sound... but imagine there is.'"""
    camera(ctx, 540, 960, 1.0 + 0.03 * lt / INTER, t=lt)
    space_bg(ctx, lt + 50)
    earth(ctx, 540, 1250, 300, lt, heat=1.0, crack=0.1)
    ctx.identity_matrix()
    a1 = seg(lt, 0.1, 0.4)
    a2 = seg(lt, 1.1, 1.4)
    text(ctx, 'В КОСМОСЕ', W / 2, 560, 104, (1, 1, 1, a1), outline=(0, 0, 0, a1), ow=14)
    text(ctx, 'ЗВУКА НЕТ', W / 2, 680, 104, (1, 1, 1, a1), outline=(0, 0, 0, a1), ow=14)
    text(ctx, 'НО ЕСЛИ ПРЕДСТАВИТЬ,', W / 2, 820, 62, alpha(hexc('#ffd21f'), a2), outline=(0, 0, 0, a2), ow=10)
    text(ctx, 'ЧТО ОН ЕСТЬ...', W / 2, 900, 62, alpha(hexc('#ffd21f'), a2), outline=(0, 0, 0, a2), ow=10)
    fade(ctx, 1 - seg(lt, 0.0, 0.3))
    fade(ctx, seg(lt, INTER - 0.25, INTER))


def render_frame(ctx, t):
    k, lt = stage_at(t)
    ctx.save()
    rect(ctx, 0, 0, W, H, (0, 0, 0, 1))
    if k < 0:
        no_sound_card(ctx, lt)
        ctx.restore()
        ctx.identity_matrix()
        post(ctx, t, vignette=0.6, grain=0.035)
        return
    ctx.save()
    if k <= 7:
        world(ctx, k, lt, t)
    elif k == 8:
        stage_planet(ctx, k, lt, t)
    elif k == 9:
        stage_wave(ctx, k, lt, t)
    else:
        stage_galaxy(ctx, k, lt, t)
    ctx.restore()
    ctx.restore()
    ctx.identity_matrix()
    post(ctx, t, vignette=0.45, grain=0.035)
    # stage transition punch + shout flash (stronger every stage)
    flash(ctx, 0.35 * math.exp(-lt * 10))
    st = lt - SHOUT_AT
    if st >= 0:
        flash(ctx, min(0.6, 0.04 * k) * math.exp(-st * 5))
    if k == 10:
        flash(ctx, seg(lt, SHOUT_AT + 5.4 / SPD, SHOUT_AT + 6.2 / SPD))
        if lt > SHOUT_AT + 6.2 / SPD:
            fade(ctx, seg(lt, STAGE - 0.8, STAGE - 0.05))
    hud(ctx, k, lt)
