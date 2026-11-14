"""Render preview stills / contact sheets: python3 stills.py t1 t2 ... or 'shots'."""
import sys, os
import cairo
from PIL import Image
from engine import W, H
import importlib
scenes = importlib.import_module('scenes2' if os.environ.get('EP') == '2' else 'scenes')

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build', 'stills')
os.makedirs(OUT, exist_ok=True)


def frame(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    scenes.render_frame(c, t)
    p = os.path.join(OUT, f'f_{t:07.2f}.png')
    s.write_to_png(p)
    return p


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == 'shots':
        sel = [int(a) for a in args[1:]] or range(len(scenes.SHOTS))
        times = []
        for i in sel:
            t0, fn, t1 = scenes.SHOTS[i]
            times += [t0 + (t1 - t0) * f for f in (0.15, 0.5, 0.92)]
    else:
        times = [float(a) for a in args]
    paths = [frame(t) for t in times]
    cols = 6
    th = 480
    tw = int(W * th / H)
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows * th))
    for i, p in enumerate(paths):
        im = Image.open(p).convert('RGB').resize((tw, th))
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    sheet.save(os.path.join(OUT, 'sheet.png'))
    print('ok', len(paths))
