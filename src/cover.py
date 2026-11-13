"""Cover / thumbnail for the video -> output/cover.png (1080x1920)."""
import os
import math
import cairo
from engine import *
from characters import *
from envs import *
from timeline import ROOT

T0 = 3.7   # fixed time for flames / noise


def title_line(ctx, s, y, size, col, glow_col=None):
    if glow_col is not None:
        ctx.save()
        text_path(ctx, s, W / 2, y, size)
        src(ctx, glow_col)
        ctx.set_line_width(40)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
        ctx.restore()
    text(ctx, s, W / 2 + 6, y + 10, size, (0, 0, 0, 0.7), outline=(0, 0, 0, 0.7), ow=22)
    text(ctx, s, W / 2, y, size, col, outline=(0.02, 0.02, 0.04, 1), ow=20)


def main():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    t = T0
    # burning city
    ctx.save()
    camera(ctx, W / 2, H / 2 + 60, 1.0)
    burning_city(ctx, t, base_y=1560, glow_amt=1.0)
    ctx.restore()
    # red haze behind the creature
    glow(ctx, 540, 900, 900, hexc('#a0101c'), 0.55)
    # monster: front view, mouth wide open, claws reaching toward the hero
    mp = dict(view='front', t=t, mouth=1.0, drool=1.0, rim=alpha(hexc('#ff4a2a'), 1.0), rim_off=(7, -4),
              hand_b=(210, -170), hand_f=(200, -200), curl=1.1, elbows_out=True, finger_spread=1.3, head=-6)
    MONSTER.draw(ctx, 540, 1460, 1.0, mp)
    # ground + smoke in front of its legs
    vgrad(ctx, 0, 1450, W, 470, [(0, (0.03, 0.02, 0.03, 0.0)), (0.35, (0.02, 0.02, 0.04, 0.95)),
                                 (1, (0.01, 0.01, 0.02, 1))])
    for i, x in enumerate((80, 380, 700, 1000)):
        radial(ctx, x, 1520, 260, hexc('#3a1e1a'), 0.6)
    # the hero in the foreground, hand over mouth, terrified
    HERO.draw(ctx, 540, 2120, 1.65, dict(t=0.9, facing=0, hand_mouth=True, eyes='tiny', brows='worried',
                                          look=(0.0, -1.0), sweat=0.6, tremble=0, backpack=True,
                                          rim=alpha(hexc('#ff8a3a'), 0.6), lit=1.0, blink=False))
    embers(ctx, t, 0, 300, W, 1500, n=70, seed=21)
    post(ctx, t, vignette=0.9, grain=0.06)
    # title
    title_line(ctx, 'НЕ ИЗДАВАЙ', 330, 118, (1, 1, 1, 1))
    title_line(ctx, 'НИ ЗВУКА', 470, 150, (1, 0.16, 0.16, 1), glow_col=(1, 0.1, 0.1, 0.35))
    # part badge
    ctx.save()
    ctx.translate(540, 590)
    ctx.rotate(-0.04)
    w = text_width(ctx, 'ЧАСТЬ 1', 60) + 70
    rrect(ctx, -w / 2, -52, w, 84, 16, hexc('#ffd43b'))
    text(ctx, 'ЧАСТЬ 1', 0, 10, 60, hexc('#111111'))
    ctx.restore()
    # bottom hook line
    title_line(ctx, 'ОНИ СЛЫШАТ ВСЁ', 1800, 76, (1, 0.84, 0.16, 1))
    out = os.path.join(ROOT, 'output', 'cover.png')
    s.write_to_png(out)
    print(out)


if __name__ == '__main__':
    main()
