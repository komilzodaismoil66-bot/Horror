"""Cover / thumbnail for 'Поезд в 03:17' -> output/cover_poezd.png (1080x1920)."""
import os
import cairo
from engine import *
from envs3 import carriage, CF, RED_LED
from chars3 import HERO, DOUBLE, PASS
import scenes3 as SC
from cover import title_line
from timeline3 import ROOT


def main():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    t = 1.3
    z = 1.85
    ctx.save()
    camera(ctx, 560, SC.HEAD_Y + (960 - 960) / z, z)
    carriage(ctx, t, x0=-600, x1=1800, moving=1.0, flick=False)
    for x, i in ((40, 0), (200, 1), (360, 3), (760, 2), (920, 5), (1080, 4)):
        PASS[i].draw(ctx, x, CF, 0.92, dict(t=t, facing=0, sit=SC.SEAT, lit=0.75, pale=0.35, head_down=1.0,
                                            eyes='closed', blink=False))
    pts = DOUBLE.draw(ctx, 560, CF, 0.92, SC.double_pose(t, head_down=0.0, eyes='tiny', mouth='grin', look=(0, 0.1),
                                                         watch=True, watch_glow=True))
    hx, hy = pts['hand_r']
    glow(ctx, hx - 14, hy - 8, 120, RED_LED, 0.55)
    HERO.draw(ctx, 330, CF + 420, 1.3, dict(t=t, facing=2, lit=0.6))
    d_ = Darkness(ctx, 0.62, color=(0.02, 0.0, 0.0))
    d_.hole(560, CF - 330, 560, 0.85)
    d_.apply()
    glow(ctx, 560, CF - 330, 380, hexc('#ff3020'), 0.16)
    ctx.restore()
    post(ctx, t, vignette=1.2, grain=0.06)
    # title: same styling as the other covers, with the LED clock digits
    title_line(ctx, 'ПОЕЗД В', 300, 112, (1, 1, 1, 1))
    ctx.save()
    glow(ctx, W / 2, 420, 520, RED_LED, 0.45)
    rrect(ctx, W / 2 - 330, 330, 660, 170, 24, (0.03, 0.01, 0.01, 0.92))
    rrect_path(ctx, W / 2 - 330, 330, 660, 170, 24)
    ctx.set_line_width(5)
    src(ctx, alpha(RED_LED, 0.7))
    ctx.stroke()
    text(ctx, '03:17', W / 2, 466, 150, RED_LED, font='DejaVu Sans Mono Bold')
    ctx.restore()
    ctx.save()
    ctx.translate(540, 575)
    ctx.rotate(-0.04)
    w = text_width(ctx, 'НЕ САДИСЬ В НЕГО', 46) + 60
    rrect(ctx, -w / 2, -46, w, 74, 16, hexc('#ffd43b'))
    text(ctx, 'НЕ САДИСЬ В НЕГО', 0, 8, 46, hexc('#111111'))
    ctx.restore()
    title_line(ctx, 'ТЫ УЖЕ ЗДЕСЬ БЫЛ...', 1830, 70, (1, 0.84, 0.16, 1))
    out = os.path.join(ROOT, 'output', 'cover_poezd.png')
    s.write_to_png(out)
    print(out)


if __name__ == '__main__':
    main()
