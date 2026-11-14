"""Cover / thumbnail for episode 2 -> output/cover2.png (1080x1920). Same layout as cover.py (episode 1)."""
import os
import math
import cairo
from engine import *
from characters import *
from envs import *
from envs2 import *
import scenes2 as SC
from cover import title_line
from timeline2 import ROOT

T0 = 5.3


def main():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    t = T0
    ground = 1600
    # the cold, foggy street from episode 2 (camera framed so the street sits low in the frame)
    ctx.save()
    camera(ctx, SC.CAR_X, 780, 1.0)
    SC.street2(ctx, t, SC.CAR_X, cold=0.6, skip=(SC.CAR_X - 900, SC.CAR_X + 900))
    ctx.restore()
    # burning skyline far behind, in cold haze
    SKY_FAR2.draw(ctx, 1250, t, -1800, 0.7, 0.55)
    SKY_MID2.draw(ctx, 1420, t, -2600, 0.8, 0.7)
    Fog(2, -200, 1300, 1250, n=16, size=300).draw(ctx, t, 0.35)
    glow(ctx, 540, 900, 900, hexc('#8a1020'), 0.35)
    # the creature rising behind the car, claws hovering over the metal
    mp = dict(view='front', t=t, mouth=0.85, drool=1.0, rim=alpha(hexc('#9fb6ff'), 1.0), rim_off=(7, -4),
              hand_b=(330, -170), hand_f=(250, -60), curl=1.15, elbows_out=True, finger_spread=1.3, head=-8)
    hands = MONSTER.draw(ctx, 540, 1460, 1.0, mp)
    # ground in front (hides the legs), fog
    vgrad(ctx, 0, 1540, W, 400, [(0, (0.03, 0.04, 0.07, 1)), (1, (0.01, 0.01, 0.02, 1))])
    rect(ctx, 0, 1590, W, 12, hexc('#262c3a'))
    Fog(3, -200, 1300, 1560, n=14, size=260).draw(ctx, t, 0.3)
    overturned_car(ctx, 600, ground, 1.95, t, 0.95, tilt=0.03)
    # the claws reach over the car: redraw the monster on top, only around its hands
    ctx.save()
    lx = hands['hand_l'][0]
    rx = hands['hand_r'][0]
    ctx.rectangle(lx - 150, 1200, 260, 340)
    ctx.rectangle(rx - 90, 1250, 260, 290)
    ctx.clip()
    MONSTER.draw(ctx, 540, 1460, 1.0, mp)
    ctx.restore()
    # the hero hiding in front of the car, hand over mouth
    P = dict(crouch_pose(), t=0.4, facing=-1, backpack=True, eyes='tiny', brows='worried', mouth='frown',
             lit=1.0, tremble=0, sweat=0.7, hand_mouth=True, look=(0.5, -1.0), blink=False,
             rim=alpha(hexc('#8fb0e8'), 0.45))
    HERO.draw(ctx, 300, 1720, 1.35, P)
    Fog(4, -200, 1300, 1750, n=10, size=240, col=hexc('#26324a')).draw(ctx, t, 0.25)
    dust(ctx, t, 0, 300, W, 1500, n=60, a=0.3)
    post(ctx, t, vignette=0.9, grain=0.06)
    cold_tint(ctx, 0.1)
    # title (same styling as part 1)
    title_line(ctx, 'ОН СОВСЕМ', 330, 118, (1, 1, 1, 1))
    title_line(ctx, 'РЯДОМ', 470, 150, (1, 0.16, 0.16, 1), glow_col=(1, 0.1, 0.1, 0.35))
    ctx.save()
    ctx.translate(540, 590)
    ctx.rotate(-0.04)
    w = text_width(ctx, 'ЧАСТЬ 2', 60) + 70
    rrect(ctx, -w / 2, -52, w, 84, 16, hexc('#ffd43b'))
    text(ctx, 'ЧАСТЬ 2', 0, 10, 60, hexc('#111111'))
    ctx.restore()
    title_line(ctx, 'НЕ ДЫШИ...', 1830, 84, (1, 0.84, 0.16, 1))
    out = os.path.join(ROOT, 'output', 'cover2.png')
    s.write_to_png(out)
    print(out)


if __name__ == '__main__':
    main()
