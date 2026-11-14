"""Episode 2 ("Окна — часть 2"): shots timed to the narration. Same characters / style as episode 1."""
import math
import random
import cairo
from engine import *
from characters import *
from envs import *
from envs2 import *
import scenes as ep1
from timeline2 import T, OFF, DUR, TOTAL, caption_chunks

CAPS = caption_chunks()
RED = hexc('#ff2a2a')
MON_RIM_FIRE = ep1.MON_RIM_FIRE
MON_RIM_COLD = ep1.MON_RIM_COLD
shake_env = ep1.shake_env
GROUND = 1380
STRIDE = 170


# =============================================================== helpers
def mon_impacts(t0, t1, speed, seed):
    """Times when a foot of monster_walk(speed, seed) hits the ground."""
    out = []
    k = math.floor((t0 * speed + seed * 0.37 - 0.25) / 0.5)
    while True:
        tk = (k * 0.5 + 0.25 - seed * 0.37) / speed
        if tk > t1:
            break
        if tk >= t0:
            out.append(tk)
        k += 1
    return out


def walker(t, x0, t0, ground, s, speed, seed):
    """Walking monster whose planted feet do not slide. Returns hip position and pose."""
    mp, dy = monster_walk(t, speed, STRIDE, seed)
    hx = x0 + 4 * STRIDE * speed * s * (t - t0)
    return hx, ground - 640 * s + dy * s, mp


def jump_pose(p):
    """p in 0..1 across the jump."""
    tuck = math.sin(math.pi * p)
    return dict(legs=(-20 - 20 * tuck, 40 + 60 * tuck, 60 * tuck + 10, 90 * tuck + 10), hip_dy=0, lean=10,
                hand_f=(40, 40 - 30 * tuck), hand_b=(-30, 60), bend_f=1, bend_b=1)


def breath_puff(ctx, x, y, t, period=1.1, a=0.35):
    ph = (t % period) / period
    if ph < 0.6:
        f = ph / 0.6
        radial(ctx, x + f * 40, y - f * 20, 14 + f * 30, hexc('#b8c8e8'), a * (1 - f))


STREET_PROPS = []
_r = random.Random(77)
_x = -800
while _x < 9000:
    STREET_PROPS.append((_r.choice(['rubble', 'rubble', 'lamp', 'wreck', 'crack']), _x, _r.randint(0, 999)))
    _x += _r.uniform(420, 820)
STREET_FOG = Fog(5, -1500, 9000, GROUND - 120, n=60, size=300)
STREET_FOG_FRONT = Fog(6, -1500, 9000, GROUND + 160, n=50, size=260, col=hexc('#26324a'))
STREET_SMOKE = [Smoke(x, 1500, seed=90 + i, n=10, size=150, rise=30, life=10, drift=12, col=hexc('#221c26'),
                      under=hexc('#3a2a2a'), spread=3) for i, x in enumerate(range(-600, 9000, 700))]


def street2(ctx, t, camx, cold=0.5, ground=GROUND, props=True, skip=None):
    """The same burning street as the end of episode 1, growing colder / foggier further away."""
    night_sky(ctx, 1.0 - cold * 0.9, horizon=0.62, x=camx - 2500, w=5000, y=-1500, h=4500)
    glow(ctx, camx + 300, 1100, 1100, FIRE1, 0.45 * (1 - cold * 0.8))
    ox = camx * 0.6
    SKY_FAR2.draw(ctx, ground - 220, t, ox - 200, 0.8 * (1 - cold * 0.5), 0.6)
    SKY_MID2.draw(ctx, ground - 60, t, ox * 0.6 + 200, 0.9 * (1 - cold * 0.5), 0.8)
    for s_ in STREET_SMOKE:
        if abs(s_.x - camx) < 1500:
            s_.y = ground - 300
            s_.draw(ctx, t, 0.5)
    STREET_FOG.draw(ctx, t, 0.22 + 0.15 * cold)
    street_ground_wide(ctx, ground, t, camx, fire=1 - cold * 0.7)
    if props:
        for kind, x, seed in STREET_PROPS:
            if abs(x - camx) > 1400 or (skip and skip[0] < x < skip[1]):
                continue
            if kind == 'rubble':
                rubble_pile(ctx, x, ground + 20, 220, 70, seed, 0.9)
            elif kind == 'lamp':
                lamp_post(ctx, x, ground + 10, bend=(seed % 7 - 3) * 0.12)
            elif kind == 'wreck':
                draw_car(ctx, x, ground + 40, 0.9, t, hexc('#2a2a30'), burning=0.0, flip=1 if seed % 2 else -1,
                         wreck=1)
                Smoke(x, ground - 60, seed=seed, n=6, size=50, rise=40, life=5, drift=6).draw(ctx, t, 0.5)
            else:
                polyline(ctx, [(x, ground + 60), (x + 40, ground + 90), (x + 30, ground + 130), (x + 90, ground + 170)],
                         4, hexc('#05070c'))


def street_front(ctx, t, camx, cold=0.5):
    STREET_FOG_FRONT.draw(ctx, t, 0.18 + 0.12 * cold)
    embers(ctx, t, camx - 700, 200, 1400, 1300, n=int(40 * (1 - cold * 0.6)), seed=12)


def hero_run(t, phase_speed=2.4):
    return run_pose(t * phase_speed)


# =============================================================== shots
def s_escape(ctx, t, lt, d):
    ep1.escape_street(ctx, t, T(1, 'выскакиваешь') - 0.35, T(1, 'убегаешь'), OFF[1] + DUR[1], fade_out=False,
                      zoom_end=0.9, ground_fn=street_ground_wide)


STEP_SPEED, STEP_SEED, STEP_S = 0.42, 2, 1.25


def s_steps(ctx, t, lt, d):
    t0 = t - lt
    g = 1500
    hx, hy, mp = walker(t, 120, t0, g, STEP_S, STEP_SPEED, STEP_SEED)
    hits = mon_impacts(t0 - 1, t0 + d, STEP_SPEED, STEP_SEED)
    sh = shake_env(t, [(h, 30) for h in hits], 5.0) + 2
    camx = hx + 260
    camera(ctx, camx, 1080, 1.0, shake=sh, t=t)
    street2(ctx, t, camx, cold=0.25, ground=g)
    # hero far ahead, running away (smaller = further)
    rx = camx + 280 + lt * 40
    HERO.draw(ctx, rx, g - 70, 0.5, dict(hero_run(t), t=t, facing=1, backpack=True, eyes='wide', mouth='scream',
                                         lit=0.75, rim=alpha(FIRE2, 0.35)))
    mp.update(t=t, rim=alpha(MON_RIM_FIRE, 0.9), rim_off=(8, -4), mouth=0.3, drool=1.0)
    MONSTER.draw(ctx, hx, hy, STEP_S, mp, facing=1)
    for h in hits:
        if 0 <= t - h < 1.2:
            p = (t - h) / 1.2
            for k in range(5):
                radial(ctx, hx + (k - 2) * 110 + p * 60 * (k - 2), g + 10 - p * 80, 90 + p * 140, hexc('#3a3440'),
                       0.5 * (1 - p))
    street_front(ctx, t, camx, 0.25)
    post(ctx, t)


RUN_T0 = None


def run_x(t, t0, t_jump):
    """Hero x during the run shot; slows slightly in the air (cinematic)."""
    v = 640
    if t < t_jump:
        return v * (t - t0)
    x = v * (t_jump - t0)
    air = min(t, t_jump + 0.62) - t_jump
    x += v * 0.75 * air
    if t > t_jump + 0.62:
        x += v * (t - t_jump - 0.62)
    return x


def s_run(ctx, t, lt, d):
    t0 = t - lt
    tj = T(2, 'перепрыгиваешь') + 0.05
    x = run_x(t, t0, tj)
    jx = run_x(tj + 0.31, t0, tj)            # rubble under the apex
    jp = seg(t, tj, tj + 0.62)
    air = 0 < jp < 1
    zoom = 1.05 + 0.18 * math.sin(math.pi * jp)
    camx = x + 120
    camera(ctx, camx, 1020 - 40 * math.sin(math.pi * jp), zoom, shake=3, t=t)
    street2(ctx, t, camx, cold=0.4, skip=(jx - 500, jx + 500))
    # the monster following, far behind in the fog
    mx, my, mp = walker(t, x - 900, t0, GROUND - 160, 0.55, 0.5, 4)
    mp.update(t=t, body=hexc('#202434'), rim=alpha(MON_RIM_FIRE, 0.45))
    MONSTER.draw(ctx, mx, my, 0.55, mp, facing=1)
    STREET_FOG.draw(ctx, t + 3, 0.25)
    # the obstacle
    rubble_pile(ctx, jx, GROUND + 30, 300, 120, 11, 1.0)
    draw_rebar(ctx, (jx - 40, GROUND - 60), (jx + 30, GROUND - 160), 12, 0.9)
    y = GROUND + 30 - 210 * math.sin(math.pi * jp)
    if air:
        P = dict(jump_pose(jp), t=t, facing=1, backpack=True, eyes='wide', brows='worried', mouth='o', lit=0.9,
                 rim=alpha(FIRE2, 0.35))
    else:
        P = dict(hero_run(t), t=t, facing=1, backpack=True, eyes='wide', brows='worried', mouth='scream',
                 mouth_open=0.4, lit=0.9, rim=alpha(FIRE2, 0.35))
    HERO.draw(ctx, x, y, 0.9, P)
    if jp >= 1 and t - tj - 0.62 < 0.6:
        p = (t - tj - 0.62) / 0.6
        radial(ctx, x, GROUND + 30, 80 + 120 * p, hexc('#4a4450'), 0.5 * (1 - p))
    street_front(ctx, t, camx, 0.4)
    post(ctx, t)


def s_quiet(ctx, t, lt, d):
    t0 = t - lt
    slow = ease_out(seg(t, t0, t0 + 0.5))
    x = 700 * lt * (1 - slow) + 140 * lt * slow
    camx = x + 60
    camera(ctx, camx, 1150, 1.55, shake=1.5, t=t)
    street2(ctx, t, camx + 4000, cold=0.55)
    if slow < 0.6:
        P = dict(hero_run(t), t=t, facing=1, backpack=True, eyes='wide', brows='worried', mouth='o', lit=0.85)
    else:
        P = dict(sneak_pose(t * 0.9), t=t, facing=1, backpack=True, eyes='wide', brows='worried', mouth='flat',
                 look=(-1.0, 0.1) if (lt % 1.6) < 0.8 else (0.8, 0.2), lit=0.85, rim=alpha(hexc('#8fb0e8'), 0.3))
    pts = HERO.draw(ctx, x, GROUND + 30, 0.9, P)
    hd = pts['head']
    breath_puff(ctx, hd[0] + 50, hd[1] + 20, t, 0.9, 0.3)
    street_front(ctx, t, camx + 4000, 0.55)
    post(ctx, t)
    cold_tint(ctx, 0.08)


CAR_X = 5200
CAR_S = 1.6


def car_scene(ctx, t, cam, cold=0.65, fog=0.3):
    camera(ctx, *cam, t=t, shake=1.2)
    street2(ctx, t, cam[0], cold=cold, skip=(CAR_X - 900, CAR_X + 900))


def s_car(ctx, t, lt, d):
    p = ease_io(lt / d)
    hx = CAR_X - 1000 + 150 * lt
    car_scene(ctx, t, (lerp(hx + 80, CAR_X - 380, p), 1140, lerp(1.45, 1.05, p)))
    HERO.draw(ctx, hx, GROUND + 30, 0.9, dict(sneak_pose(t * 0.9), t=t, facing=1, backpack=True, eyes='wide',
                                              brows='worried', mouth='o' if lt > 1 else 'flat', look=(1, 0),
                                              lit=0.85))
    overturned_car(ctx, CAR_X, GROUND + 20, CAR_S, t, 0.9, tilt=0.03)
    hl = seg(t, T(3, 'перевернутую'), T(3, 'перевернутую') + 0.3) * (1 - seg(t, T(3, 'машину', end=True),
                                                                              T(3, 'машину', end=True) + 0.6))
    if hl > 0:
        glow(ctx, CAR_X, GROUND - 120, 420, hexc('#8fb0e8'), 0.18 * hl)
    street_front(ctx, t, CAR_X, 0.65)
    post(ctx, t)
    cold_tint(ctx, 0.14)


HIDE_X = CAR_X - 330


def hero_hiding(t, frozen=True, tremble=1.0):
    P = dict(crouch_pose(), t=t, facing=-1, backpack=True, eyes='tiny', brows='worried', mouth='frown',
             lit=0.85, tremble=tremble, sweat=0.8, hand_mouth=True, look=(0.6, -0.3))
    return P


def s_hide(ctx, t, lt, d):
    t0 = t - lt
    t_dash = T(3, 'быстро')
    t_freeze = T(3, 'замираешь')
    car_scene(ctx, t, (CAR_X - 260, 1180, 1.25))
    overturned_car(ctx, CAR_X, GROUND + 20, CAR_S, t, 0.9, tilt=0.03)
    dash = seg(t, t_dash, t_dash + 0.55)
    if dash < 1:
        x = lerp(CAR_X - 900, HIDE_X, ease_out(dash))
        HERO.draw(ctx, x, GROUND + 70, 0.9, dict(hero_run(t), t=t, facing=1, backpack=True, eyes='wide',
                                                  brows='worried', mouth='o', lit=0.85))
    else:
        c = ease_out(seg(t, t_dash + 0.55, t_dash + 0.8))
        P = hero_hiding(t, tremble=0.3 if t > t_freeze else 1.2)
        P['hip_dy'] = lerp(60, 170, c)
        HERO.draw(ctx, HIDE_X, GROUND + 70, 0.9, P)
    street_front(ctx, t, CAR_X, 0.65)
    post(ctx, t)
    cold_tint(ctx, 0.14)
    if t > t_freeze:
        # freeze: brief desaturating flash
        fade(ctx, 0.25 * (1 - seg(t, t_freeze, t_freeze + 0.5)), (0.6, 0.7, 0.9))


PASS_SPEED, PASS_SEED, PASS_S = 0.2, 5, 0.9
PASS_T0 = None


def pass_monster(t):
    t0 = OFF[4] - 0.6
    hx, hy, mp = walker(t, CAR_X - 620, t0, GROUND - 40, PASS_S, PASS_SPEED, PASS_SEED)
    return hx, hy, mp


def s_pass(ctx, t, lt, d):
    car_scene(ctx, t, (CAR_X - 150, 1020, 0.95 + 0.04 * lt))
    hx, hy, mp = pass_monster(t)
    mp.update(t=t, rim=alpha(MON_RIM_COLD, 0.9), rim_off=(7, -4), head=-10 + jerk(t, 1.8, 3) * 16,
              neck=58 + jerk(t, 1.1, 4) * 10, mouth=0.15, drool=1.0)
    MONSTER.draw(ctx, hx, hy, PASS_S, mp, facing=1)
    overturned_car(ctx, CAR_X, GROUND + 20, CAR_S, t, 0.9, tilt=0.03)
    HERO.draw(ctx, HIDE_X, GROUND + 70, 0.9, hero_hiding(t, tremble=0.6))
    street_front(ctx, t, CAR_X, 0.65)
    post(ctx, t)
    cold_tint(ctx, 0.14)


def s_hands(ctx, t, lt, d):
    t_touch = T(4, 'касаются')
    hx, hy, mp = pass_monster(t)
    # the long arm drifts over the car; claws hover a few centimetres above the metal
    top = GROUND + 20 - 170 * CAR_S
    tx = CAR_X - 120 + 140 * math.sin(lt * 0.7)
    ty = top - 40 + 28 * (1 - seg(t, t_touch - 0.3, t_touch + 0.4)) * 2 - 22 * math.sin(lt * 3) ** 2
    mp.update(t=t, rim=alpha(MON_RIM_COLD, 0.95), rim_off=(7, -4), head=-25, neck=70, mouth=0.25, drool=1.0,
              hand_f=((tx - hx) / PASS_S, (ty - hy) / PASS_S), curl=0.55 + 0.15 * math.sin(t * 4))
    z = lerp(1.55, 1.85, ease_io(lt / d))
    car_scene(ctx, t, (CAR_X - 200, top + 60, z))
    MONSTER.draw(ctx, hx, hy, PASS_S, mp, facing=1)
    overturned_car(ctx, CAR_X, GROUND + 20, CAR_S, t, 0.9, tilt=0.03)
    HERO.draw(ctx, HIDE_X, GROUND + 70, 0.9, dict(hero_hiding(t, tremble=0.5), look=(-0.4, -1.0)))
    street_front(ctx, t, CAR_X, 0.65)
    post(ctx, t)
    cold_tint(ctx, 0.14)


def s_breath(ctx, t, lt, d):
    car_scene(ctx, t, (HIDE_X + 5, GROUND - 215, 3.1 + 0.15 * math.sin(lt * 7.5) ** 8))
    overturned_car(ctx, CAR_X, GROUND + 20, CAR_S, t, 0.9, tilt=0.03)
    P = hero_hiding(t, tremble=0.25)
    P.update(eyes='tiny', sweat=seg(lt, 0, 1.5) + 0.3, look=(-0.2, -0.6))
    HERO.draw(ctx, HIDE_X, GROUND + 70, 0.9, P)
    # the creature's shadow sliding over the hero
    sx = lerp(-300, 1400, lt / d)
    ctx.save()
    ctx.identity_matrix()
    g = cairo.LinearGradient(sx - 400, 0, sx + 400, 0)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(0.5, 0, 0, 0.02, 0.55)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(g)
    ctx.paint()
    ctx.restore()
    post(ctx, t, vignette=1.2)
    cold_tint(ctx, 0.16)


def s_leave(ctx, t, lt, d):
    p = lt / d
    car_scene(ctx, t, (CAR_X + 250, 1000, 0.85))
    # walking away into the fog: smaller and higher = further
    s = lerp(0.85, 0.5, p)
    t0 = t - lt
    mp, dy = monster_walk(t, 0.22, STRIDE, PASS_SEED)
    hx = CAR_X + 150 + 520 * p
    hy = GROUND - 40 - 260 * p - 640 * s + dy * s
    mp.update(t=t, body=mix(hexc('#1a1b22'), hexc('#2a3448'), p), rim=alpha(MON_RIM_COLD, 0.8 * (1 - p)),
              head=jerk(t, 1.5, 2) * 10)
    MONSTER.draw(ctx, hx, hy, s, mp, facing=1)
    Fog(9, CAR_X - 200, CAR_X + 1400, GROUND - 260, n=18, size=320).draw(ctx, t, 0.25 + 0.35 * p)
    overturned_car(ctx, CAR_X, GROUND + 20, CAR_S, t, 0.9, tilt=0.03)
    HERO.draw(ctx, HIDE_X, GROUND + 70, 0.9, hero_hiding(t, tremble=0.4))
    street_front(ctx, t, CAR_X, 0.7)
    post(ctx, t)
    cold_tint(ctx, 0.16)


def s_peek(ctx, t, lt, d):
    t_peek = T(5, 'выглядываешь')
    t_go = T(5, 'продолжаешь')
    rise = ease_io(seg(t, t_peek - 0.2, t_peek + 0.5))
    go = seg(t, t_go, t_go + 2.0)
    camx = lerp(HIDE_X + 120, HIDE_X + 500, ease_io(go))
    car_scene(ctx, t, (camx, GROUND - 230, 1.6))
    overturned_car(ctx, CAR_X, GROUND + 20, CAR_S, t, 0.9, tilt=0.03)
    if go <= 0:
        P = hero_hiding(t, tremble=0.3)
        P.update(facing=1, hand_mouth=False, look=(1, -0.2) if rise > 0.5 else (0.3, 0), eyes='wide',
                 mouth='flat', sweat=0.5)
        P['hip_dy'] = lerp(170, 60, rise)
        P['lean'] = lerp(-8, 20, rise)
        HERO.draw(ctx, HIDE_X + 30, GROUND + 70, 0.9, P)
    else:
        x = HIDE_X + 30 + 330 * go
        HERO.draw(ctx, x, GROUND + 70, 0.9, dict(sneak_pose(t * 0.9), t=t, facing=1, backpack=True, eyes='open',
                                                  brows='worried', mouth='flat', lit=0.85))
    street_front(ctx, t, camx, 0.7)
    post(ctx, t)
    cold_tint(ctx, 0.16)


BUNKER_X = 640
OUT_FOG = Fog(12, -800, 2000, 1150, n=24, size=320, col=hexc('#2a3856'))


def s_outskirts(ctx, t, lt, d):
    t_b = T(6, 'бункер')
    p = ease_io(lt / d)
    camera(ctx, lerp(500, 600, p), lerp(1020, 1000, p), lerp(1.25, 1.45, p), shake=1, t=t)
    outskirts(ctx, t)
    OUT_FOG.draw(ctx, t, 0.35)
    for i, x in enumerate((-150, 220, 1500)):
        dead_tree(ctx, x, 1160 + i * 6, 300 + 60 * i, 30 + i)
    a = power_pole(ctx, 60, 1165, 480, -0.05)
    b = power_pole(ctx, 420, 1160, 470, 0.12)
    wire(ctx, a, b, 50)
    wire(ctx, (a[0], a[1] + 30), (b[0], b[1] + 26), 70)
    sg = seg(t, t_b, t_b + 0.3) * (1 - seg(t, t_b + 1.0, t_b + 1.8))
    bunker_exterior(ctx, t, BUNKER_X, 1180, 1.0, 0.85, sign_glow=sg)
    door_rubble(ctx, BUNKER_X + 40, 1182, 1.0, 0.85)
    if sg > 0:
        glow(ctx, BUNKER_X + 130, 1180 - 300, 200, hexc('#ff6a50'), 0.3 * sg)
    hx = lerp(180, 420, seg(lt, 0, d * 0.6))
    walking = lt < d * 0.6
    P = dict(walk_pose(t * 1.4) if walking else {}, t=t, facing=1, backpack=True, eyes='wide' if not walking else 'open',
             brows='worried', mouth='o' if not walking else 'flat', look=(1, 0), lit=0.8)
    HERO.draw(ctx, hx, 1205, 0.55, P)
    OUT_FOG.draw(ctx, t + 4, 0.25, dx=200)
    dust(ctx, t, 0, 300, 1080, 1100, n=40, a=0.25)
    post(ctx, t)
    cold_tint(ctx, 0.08)


def entrance_stage(ctx, t, cam, hero=None, sq=None):
    camera(ctx, *cam, shake=1, t=t)
    outskirts(ctx, t, horizon=900, city_glow=0.6)
    OUT_FOG.draw(ctx, t, 0.3)
    door = bunker_exterior(ctx, t, 420, 1400, 1.6, 0.9)
    door_rubble(ctx, 470, 1404, 1.6, 0.9)
    dust(ctx, t, 0, 600, 1300, 1000, n=50, a=0.3)


def s_rubble(ctx, t, lt, d):
    p = ease_io(lt / d)
    entrance_stage(ctx, t, (lerp(560, 640, p), lerp(1180, 1080, p), lerp(1.0, 1.25, p)))
    hx = lerp(-60, 140, seg(lt, 0, d * 0.5))
    HERO.draw(ctx, hx, 1420, 0.85, dict(walk_pose(t * 1.4) if lt < d * 0.5 else {}, t=t, facing=1, backpack=True,
                                        eyes='open', brows='worried', mouth='flat', look=(0.6, -0.8), lit=0.85))
    post(ctx, t)
    cold_tint(ctx, 0.08)


def s_squeeze(ctx, t, lt, d):
    p = seg(lt, 0, d)
    camera(ctx, 600, 1040, 1.35, shake=1.5, t=t)
    outskirts(ctx, t, horizon=900, city_glow=0.6)
    OUT_FOG.draw(ctx, t, 0.3)
    bunker_exterior(ctx, t, 420, 1400, 1.6, 0.9, gap_open=True)
    # path: up the rubble slope to the gap at the top-left of the door
    gap = (420 + 1.6 * 70, 1400 - 1.6 * 215)
    path = [(140, 1420), (330, 1260), gap, (gap[0] + 120, gap[1] + 20)]
    k = min(2, int(p * 3))
    f = p * 3 - k
    x = lerp(path[k][0], path[k + 1][0], f)
    y = lerp(path[k][1], path[k + 1][1], f)
    inside = k == 2
    if inside:
        ctx.save()
        # visible only inside the dark gap
        poly(ctx, [(420 + 1.6 * 46, 1400 - 1.6 * 246), (420 + 1.6 * 160, 1400 - 1.6 * 246),
                   (420 + 1.6 * 130, 1400 - 1.6 * 180), (420 + 1.6 * 46, 1400 - 1.6 * 160)])
        ctx.clip()
    P = dict(walk_pose(t * 1.1, 0.7), t=t, facing=1, backpack=True, eyes='squint', brows='worried', mouth='grit',
             lean=35 + 20 * (k > 0), lit=0.85 * (1 - 0.6 * f if inside else 1), hand_f=(70, 30), hand_b=(50, 50))
    HERO.draw(ctx, x, y + 20, 0.85, P)
    if inside:
        ctx.restore()
    door_rubble(ctx, 470, 1404, 1.6, 0.9)
    dust(ctx, t, 300, 900, 600, 500, n=40, a=0.45, col=(0.7, 0.68, 0.62))
    post(ctx, t)
    cold_tint(ctx, 0.08)


def room_camera(ctx, t, cx, cy, z, sh=0.0):
    camera(ctx, cx, cy, z, shake=sh, t=t)
    rect(ctx, -3000, -3000, 8000, 8000, hexc('#07090e'))


def s_door(ctx, t, lt, d):
    t_close = T(7, 'дверь') + 0.05
    sh = shake_env(t, [(t_close, 34)], 3.5) + 1
    room_camera(ctx, t, 420, 1300, 1.7, sh)
    op = 1 - ease_in(seg(t, t - lt, t_close))
    out_light = op
    bunker_room(ctx, t, lit=0.8, door_open=op * 0.85, outside_light=out_light)
    dx, dy, dw, dh = DOOR_IN
    # hero pushing the heavy door (it slides closed along the wall)
    edge = dx + dw * (1 - op * 0.85)
    P = dict(walk_pose(t * 0.8, 0.5), t=t, facing=-1, backpack=True, eyes='squint', brows='angry', mouth='grit',
             lean=25, hand_f=(70, 20), hand_b=(60, 30), lit=0.9, rim=alpha(hexc('#8fb0e8'), 0.4 * op))
    if t > t_close:
        P.update(eyes='wide', mouth='o', lean=5, legs=(0, 0, 0, 0), hand_f=(30, 120), hand_b=(20, 120))
    HERO.draw(ctx, edge + 95, ROOM['floor'], 0.9, P)
    # falling dust after the slam
    if t > t_close:
        lt2 = t - t_close
        r = random.Random(3)
        for i in range(40):
            x = r.uniform(150, 900)
            y = ROOM['ceil'] + 60 + (lt2 * r.uniform(200, 400)) % 420
            circle(ctx, x, y, r.uniform(1.5, 3.5), (0.75, 0.72, 0.65, 0.6 * (1 - seg(lt2, 0.5, 1.5))))
    dk = Darkness(ctx, lerp(0.85, 0.5, out_light))
    dk.hole(dx + dw / 2, dy + dh / 2, 600 * max(out_light, 0.05), 0.9)
    dk.apply()
    post(ctx, t)
    flash(ctx, 0.25 * math.exp(-max(0, t - t_close) * 8) * (t > t_close), (0.6, 0.65, 0.75))


def flashlight_ang(t, t_on):
    lt = t - t_on
    return 180 + 25 * math.sin(lt * 1.3) - 10        # degrees in local (facing) coords


def s_dark(ctx, t, lt, d):
    t_on = T(8, 'темно') + 0.15
    room_camera(ctx, t, 560, 1290, 1.25 + 0.05 * lt)
    bunker_room(ctx, t, lit=1.0)
    on = t > t_on
    # sweep across the room
    sweep = seg(t, t_on, t_on + d)
    ang = lerp(-35, 15, ease_io(sweep)) + 8 * math.sin(t * 2)
    P = dict(t=t, facing=1, backpack=True, eyes='wide', brows='worried', mouth='flat', lit=0.9,
             flashlight=ang if on else 40, hand_f=(60, 40), bend_f=1)
    pts = HERO.draw(ctx, 330, ROOM['floor'], 0.9, P)
    dk = Darkness(ctx, 0.92)
    if on:
        lx, ly = pts['lens']
        a = math.radians(ang)
        dk.cone(lx, ly, a, 0.42, 1150, 1.0)
        dk.hole(lx, ly, 200, 0.6)
        dk.hole(lx + math.cos(a) * 600, ly + math.sin(a) * 600, 420, 0.35)
    dk.apply()
    if on:
        # dust motes visible inside the beam
        lx, ly = pts['lens']
        a = math.radians(ang)
        r = random.Random(8)
        for i in range(90):
            dist = r.uniform(40, 800)
            off = r.uniform(-0.3, 0.3)
            px = lx + math.cos(a + off) * dist + math.sin(t * 0.8 + i) * 12
            py = ly + math.sin(a + off) * dist + ((t * 15 + i * 37) % 60) - 30
            circle(ctx, px, py, r.uniform(1.2, 3), (0.9, 0.88, 0.8, 0.5 * (1 - dist / 800)))
    post(ctx, t)


def s_safe(ctx, t, lt, d):
    t_lamp = T(8, 'впервые') - 0.1
    t_sit = T(8, 'чувствуешь') - 0.3
    t_safe = T(8, 'безопасности')
    lamp = ease_out(seg(t, t_lamp, t_lamp + 0.6)) * (0.9 + 0.1 * noise(t * 9, 4))
    z = lerp(1.45, 1.8, ease_io(lt / d))
    room_camera(ctx, t, 500, 1330, z)
    lpos = bunker_room(ctx, t, lit=0.9, lantern=lamp)
    sit = ease_io(seg(t, t_sit, t_sit + 0.9))
    P = dict(t=t, facing=1, backpack=True, lit=0.95, rim=alpha(hexc('#ffc46b'), 0.4 * lamp),
             eyes='closed' if t > t_safe else 'open', blink=False, brows='worried' if t < t_safe else 'neutral',
             mouth='smile' if t > t_safe + 0.2 else 'flat', hand_f=(40, 140), hand_b=(20, 140))
    if sit > 0:
        P.update(legs=(lerp(0, 85, sit), lerp(0, 15, sit), lerp(0, 80, sit), lerp(0, 25, sit)),
                 hip_dy=lerp(0, 165, sit), lean=lerp(0, -12, sit), hand_f=(lerp(40, 70, sit), lerp(140, 110, sit)))
    HERO.draw(ctx, 380, ROOM['floor'] + 4, 0.9, P)
    if t > t_safe:
        # a long relieved exhale
        hp = (380 + 30, ROOM['floor'] - 330)
        breath_puff(ctx, hp[0] + 40, hp[1], t - t_safe, 2.0, 0.25)
    dk = Darkness(ctx, 0.93)
    dk.hole(lpos[0], lpos[1], 520 * max(lamp, 0.01), 0.95)
    dk.hole(330, ROOM['floor'] - 200, 220, 0.4)
    dk.apply()
    if lamp > 0:
        glow(ctx, lpos[0], lpos[1], 420, hexc('#ffb860'), 0.35 * lamp)
    dust(ctx, t, 250, 1100, 500, 380, n=30, a=0.35 * lamp, col=(1, 0.85, 0.6), size=2)
    post(ctx, t)


SURFACE = 700


def home_scene(ctx, t, z, cy, monster_x, monster_stop=0.0):
    camera(ctx, 540, cy, z, t=t)
    # sky + ruins on the surface
    vgrad(ctx, -2500, -2500, 6000, SURFACE + 2500, [(0, hexc('#050912')), (0.7, hexc('#0e1a33')),
                                                   (1, hexc('#22314f'))])
    glow(ctx, -600, SURFACE - 100, 1200, FIRE1, 0.3)
    ctx.save()
    ctx.translate(-1500, SURFACE)
    ctx.scale(0.55, 0.55)
    SKY_FAR2.draw(ctx, 0, t, 0, 0.7, 0.6)
    ctx.restore()
    OUT_FOG.draw(ctx, t, 0.3, dx=-200)
    # monster walking on the surface above the shelter
    s = 0.6
    mp, dy = monster_walk(t, 0.2 * (1 - monster_stop), STRIDE, 7)
    if monster_stop > 0:
        mp.update(neck=lerp(mp['neck'], 95, monster_stop), head=lerp(mp['head'], 40, monster_stop),
                  torso=lerp(mp['torso'], 45, monster_stop))
    mp.update(t=t, rim=alpha(MON_RIM_COLD, 0.8), rim_off=(6, -3))
    MONSTER.draw(ctx, monster_x, SURFACE - 640 * s + dy * s, s, mp, facing=1)
    rect(ctx, -2500, SURFACE - 4, 6000, 10, hexc('#1a2230'))
    earth_section(ctx, t, SURFACE)
    lpos = bunker_room(ctx, t, lit=0.9, lantern=0.95)
    P = dict(t=t, facing=1, backpack=True, lit=0.95, rim=alpha(hexc('#ffc46b'), 0.4), eyes='closed', blink=False,
             mouth='smile', legs=(85, 15, 80, 25), hip_dy=165, lean=-12, hand_f=(70, 110), hand_b=(20, 140))
    HERO.draw(ctx, 380, ROOM['floor'] + 4, 0.9, P)
    return lpos


FINAL_Z, FINAL_CY = 0.5, -340


def s_home(ctx, t, lt, d):
    p = ease_io(seg(lt, 0, d))
    z = lerp(1.8, FINAL_Z, p)
    cy = lerp(1330, FINAL_CY, p)
    lpos = home_scene(ctx, t, z, cy, lerp(-420, -150, lt / d))
    dk = Darkness(ctx, 0.6)
    dk.hole(lpos[0], lpos[1], 560, 0.95)
    dk.hole(540, SURFACE - 300, 1400, 0.45)
    dk.apply()
    glow(ctx, lpos[0], lpos[1], 420, hexc('#ffb860'), 0.35)
    post(ctx, t)


# ---------------------------------------------------------------- poll
def wrap(ctx, s, size, width, font='Montserrat Black'):
    words = s.split()
    lines_, cur = [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        if text_width(ctx, test, size, font) > width and cur:
            lines_.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines_.append(cur)
    return lines_


def poll_card(ctx, y, letter, body, col, p, active, size=38, lh=47):
    if p <= 0:
        return 0
    s = back_out(clamp(p / 0.35), 1.4)
    a = clamp(p / 0.2)
    x0, w = 60, 960
    lines_ = wrap(ctx, body, size, w - 210)
    h = 56 + len(lines_) * lh
    ctx.save()
    ctx.translate(W / 2, y + h / 2)
    ctx.scale(s, s)
    ctx.translate(-W / 2, -(y + h / 2))
    if active > 0:
        glow(ctx, W / 2, y + h / 2, 560, col, 0.22 * active)
    rrect(ctx, x0, y, w, h, 30, (0.03, 0.04, 0.08, 0.82 * a))
    rrect_path(ctx, x0, y, w, h, 30)
    ctx.set_line_width(5 + 3 * active)
    src(ctx, alpha(col, a * (0.6 + 0.4 * active)))
    ctx.stroke()
    circle(ctx, x0 + 88, y + h / 2, 54, alpha(col, a))
    text(ctx, letter, x0 + 88, y + h / 2 + 27, 76, (0.05, 0.05, 0.08, a))
    ty = y + h / 2 - (len(lines_) - 1) * lh / 2 + size * 0.36
    for i, ln in enumerate(lines_):
        text(ctx, ln, x0 + 172, ty + i * lh, size, (1, 1, 1, a), anchor='left')
    ctx.restore()
    return h


FINAL_Z, FINAL_CY = 0.5, -340


def s_poll(ctx, t, lt, d):
    t_q, t_a, t_b, t_c = OFF[10], OFF[11], OFF[12], OFF[13]
    stop = ease_io(seg(t, t_c - 1.0, t_c + 1.5))
    mx = lerp(-150, 600, ease_out(seg(t, t - lt, t_c - 0.5)))
    lpos = home_scene(ctx, t, FINAL_Z, FINAL_CY, mx, stop)
    dk = Darkness(ctx, 0.55)
    dk.hole(lpos[0], lpos[1], 560, 0.95)
    dk.hole(540, SURFACE - 300, 1400, 0.5)
    dk.hole(mx, SURFACE - 350, 500, 0.6)
    dk.apply()
    glow(ctx, lpos[0], lpos[1], 420, hexc('#ffb860'), 0.35)
    post(ctx, t)
    ctx.save()
    ctx.identity_matrix()
    # darken the upper part (text area), keep the shelter visible at the bottom
    g = cairo.LinearGradient(0, 0, 0, H)
    k = seg(t, t_q - 0.3, t_q + 0.3)
    g.add_color_stop_rgba(0, 0, 0, 0.02, 0.6 * k)
    g.add_color_stop_rgba(0.6, 0, 0, 0.02, 0.45 * k)
    g.add_color_stop_rgba(0.75, 0, 0, 0.02, 0.0)
    ctx.set_source(g)
    ctx.paint()
    qa = back_out(seg(t, t_q - 0.1, t_q + 0.25), 1.4)
    if qa > 0:
        ctx.save()
        ctx.translate(W / 2, 320)
        ctx.scale(qa, qa)
        ctx.translate(-W / 2, -320)
        text(ctx, 'ТЫ НАШЁЛ ЗАБРОШЕННЫЙ БУНКЕР.', W / 2, 250, 44, (1, 1, 1, 1), outline=(0, 0, 0, 1), ow=12)
        text(ctx, 'ЧТО БУДЕШЬ', W / 2, 340, 80, hexc('#ffd43b'), outline=(0, 0, 0, 1), ow=16)
        text(ctx, 'ДЕЛАТЬ ДАЛЬШЕ?', W / 2, 425, 80, hexc('#ffd43b'), outline=(0, 0, 0, 1), ow=16)
        ctx.restore()
    act_a = seg(t, t_a, t_a + 0.2) * (1 - seg(t, t_b - 0.2, t_b + 0.1))
    act_b = seg(t, t_b, t_b + 0.2) * (1 - seg(t, t_c - 0.2, t_c + 0.1))
    poll_card(ctx, 480, 'А', 'УКРЕПИТЬ БУНКЕР, УСТАНОВИТЬ ШУМОИЗОЛЯЦИЮ И ЗАПАСТИСЬ ЕДОЙ И ВОДОЙ',
              hexc('#3ecf6e'), t - t_a + 0.1, act_a)
    poll_card(ctx, 715, 'Б', 'РИСКНУТЬ И ОТПРАВИТЬСЯ В СУПЕРМАРКЕТ ЗА ПРИПАСАМИ, ПОКА МОНСТРЫ НЕ ВЕРНУЛИСЬ',
              hexc('#ff4a4a'), t - t_b + 0.1, act_b)
    cp = t - t_c + 0.1
    if cp > 0:
        s = back_out(clamp(cp / 0.35), 1.6) * (1 + 0.03 * math.sin(t * 6) * (cp > 0.5))
        cy = 1075
        ctx.save()
        ctx.translate(W / 2, cy)
        ctx.scale(s, s)
        ctx.translate(-W / 2, -cy)
        rrect(ctx, 60, 955, 960, 250, 30, (0.75, 0.05, 0.08, 0.93))
        text(ctx, 'ПИШИ «А» ИЛИ «Б»', W / 2, 1027, 66, (1, 1, 1, 1), outline=(0.2, 0, 0, 1), ow=10)
        text(ctx, 'В КОММЕНТАРИЯХ!', W / 2, 1100, 66, hexc('#ffd43b'), outline=(0.2, 0, 0, 1), ow=10)
        text(ctx, 'ТВОЙ ВЫБОР ОПРЕДЕЛИТ', W / 2, 1147, 34, (1, 1, 1, 0.95))
        text(ctx, 'ПРОДОЛЖЕНИЕ ИСТОРИИ!', W / 2, 1187, 34, (1, 1, 1, 0.95))
        ctx.restore()
    ctx.restore()


# =============================================================== shot list
def build_shots():
    S = []

    def add(t0, fn):
        S.append([t0, fn])

    add(0.0, s_escape)
    add(OFF[2] - 0.05, s_steps)
    add(T(2, 'ты') - 0.1, s_run)
    add(T(2, 'стараешься') - 0.15, s_quiet)
    add(OFF[3] - 0.05, s_car)
    add(T(3, 'быстро') - 0.1, s_hide)
    add(OFF[4] - 0.05, s_pass)
    add(T(4, 'его') - 0.1, s_hands)
    add(T(4, 'ты') - 0.1, s_breath)
    add(OFF[5] - 0.05, s_leave)
    add(T(5, 'ты') - 0.1, s_peek)
    add(OFF[6] - 0.05, s_outskirts)
    add(T(6, 'его') - 0.1, s_rubble)
    add(OFF[7] - 0.05, s_squeeze)
    add(T(7, 'закрываешь') - 0.15, s_door)
    add(OFF[8] - 0.05, s_dark)
    add(T(8, 'но') - 0.1, s_safe)
    add(OFF[9] - 0.05, s_home)
    add(OFF[10] - 0.25, s_poll)
    for i in range(len(S)):
        S[i].append(S[i + 1][0] if i + 1 < len(S) else TOTAL + 1)
    return S


SHOTS = build_shots()


def hud(ctx, t):
    if t > OFF[10] - 0.3:
        return
    m = 23 + int(t / 14)
    s = f'НОЧЬ — 03:{m:02d}'
    ctx.save()
    ctx.identity_matrix()
    w = text_width(ctx, s, 34, 'DejaVu Sans Mono Bold') + 70
    rrect(ctx, W / 2 - w / 2, 120, w, 62, 10, (0.03, 0.02, 0.04, 0.75))
    if int(t * 1.5) % 2 == 0:
        circle(ctx, W / 2 - w / 2 + 30, 151, 9, (1, 0.15, 0.15, 1))
    text(ctx, s, W / 2 + 14, 163, 34, (1, 0.25, 0.25, 1), font='DejaVu Sans Mono Bold')
    # episode tag at the very start
    a = seg(t, 0.1, 0.4) * (1 - seg(t, 2.6, 3.1))
    if a > 0:
        tw = text_width(ctx, 'ЧАСТЬ 2', 44) + 50
        rrect(ctx, W / 2 - tw / 2, 205, tw, 64, 14, alpha(hexc('#ffd43b'), a))
        text(ctx, 'ЧАСТЬ 2', W / 2, 252, 44, (0.07, 0.07, 0.07, a))
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
    ep1.captions(ctx, t, CAPS, fit=840)
