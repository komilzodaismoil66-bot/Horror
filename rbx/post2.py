"""Post: upscale to 1080x1920, rain, grade, shake on hits, flashes, grain, TO BE CONTINUED card, mux audio."""
import json
import math
import os
import random
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EV = json.load(open(os.path.join(HERE, 'events2.json')))
FPS = 24
W, H = 1080, 1920
END = EV['cut']
CARD = 3.0
Z = 1.06
FONT = os.path.join(ROOT, 'fonts', 'Montserrat_900Black.ttf')
rng = np.random.default_rng(1)

# rain drops: x, y phase, speed, length
DROPS = [(random.Random(i).uniform(-200, W + 200), random.Random(i + 1).random(), random.Random(i + 2).uniform(0.8, 1.3),
          random.Random(i + 3).uniform(40, 120)) for i in range(420)]
GRAIN = [rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W]
VIG = 1 - 0.55 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.47) / (H * 0.62)) ** 2, 0, 1)
VIG = VIG[..., None].astype(np.float32)


def shake(t):
    dx = dy = 0.0
    for te, amp in EV['shakes']:
        if 0 <= t - te < 0.6:
            k = amp * math.exp(-(t - te) * 7)
            dx += math.sin(t * 91 + te) * k
            dy += math.cos(t * 77 + te * 3) * k
    for t0, t1 in EV['tremor']:
        if t0 <= t <= t1:
            a = 5 * min(1, (t - t0) / 0.8) * (1 if t < t1 - 0.5 else (t1 - t) / 0.5)
            dx += math.sin(t * 63) * a
            dy += math.cos(t * 71) * a
    return dx, dy


def flash(t):
    f = 0.0
    for te, size in EV['impacts']:
        if 0 <= t - te < 0.15:
            f = max(f, min(0.55, 0.18 * size) * (1 - (t - te) / 0.15))
    return f


def rain_layer(t, strength):
    im = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(im)
    ang = 0.18
    for (x, ph, sp, L) in DROPS:
        y = ((ph + t * sp * 1.6) % 1.0) * (H + 300) - 150
        xx_ = x + y * ang
        d.line([(xx_, y), (xx_ + L * ang, y + L)], fill=int(90 * strength), width=2)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255


def grade(a, t):
    # teal shadows / warm highlights, gentle S-curve, lifted blacks (filmic)
    lum = a.mean(axis=2, keepdims=True)
    shadow = np.clip(1 - lum * 2.2, 0, 1)
    a = a + shadow * np.array([-0.012, 0.004, 0.022], np.float32)
    a = np.clip(a, 0, 1)
    a = a * a * (3 - 2 * a) * 0.35 + a * 0.65
    return a * 0.96 + 0.018


def process(fr, img):
    t = (fr - 1) / FPS
    dx, dy = shake(t)
    zw, zh = int(W * Z), int(H * Z)
    big = img.convert('RGB').resize((zw, zh), Image.LANCZOS)
    mx, my = (zw - W) // 2, (zh - H) // 2
    ox = mx + int(max(-mx, min(mx, dx * 2)))
    oy = my + int(max(-my, min(my, dy * 2)))
    a = np.asarray(big.crop((ox, oy, ox + W, oy + H)), np.float32) / 255
    # chromatic aberration on the hits
    f = flash(t)
    if f > 0.1:
        s = int(4 + 14 * f)
        a[..., 0] = np.roll(a[..., 0], s, axis=1)
        a[..., 2] = np.roll(a[..., 2], -s, axis=1)
    a = grade(a, t)
    a = a + rain_layer(t, 1.0) * np.array([0.75, 0.82, 1.0], np.float32) * 0.55
    a = a * VIG
    a = a + f
    if t < 1.0:
        a = a * t
    if t > END - 0.25:
        a = a * max(0.0, (END - t) / 0.25)
    g = GRAIN[fr % len(GRAIN)]
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
    a = a + g * 0.022
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def card(i):
    t = i / FPS
    im = Image.new('RGB', (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    a = min(1.0, max(0.0, (t - 0.35) / 0.4))
    if a > 0:
        f1 = ImageFont.truetype(FONT, 92)
        col = (int(235 * a), int(235 * a), int(240 * a))
        for k, line in enumerate(('TO BE', 'CONTINUED')):
            w = d.textlength(line, font=f1)
            d.text(((W - w) / 2 + (6 if k else -6) * (1 - a), 860 + k * 110), line, font=f1, fill=col)
        d.line([(300, 1110), (780, 1110)], fill=(int(200 * a), int(25 * a), int(30 * a)), width=6)
    return np.asarray(im)


def main():
    FD = os.path.join(HERE, os.environ.get('FRAMES', 'frames2'))
    frames = sorted(f for f in os.listdir(FD) if f.endswith('.png') and os.path.getsize(os.path.join(FD, f)) > 0)
    if os.environ.get('LIMIT'):
        frames = frames[:int(os.environ['LIMIT'])]
    out = os.environ.get('OUTFILE') or os.path.join(ROOT, 'output', 'roblox_cinematic_full.mp4')
    tmp = os.path.join(HERE, 'build', 'video2.mp4')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                          '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for name in frames:
        fr = int(name[:4])
        p.stdin.write(process(fr, Image.open(os.path.join(FD, name))).tobytes())
    for i in range(int(CARD * FPS)):
        p.stdin.write(card(i).tobytes())
    p.stdin.close()
    p.wait()
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-i', os.path.join(HERE, 'build', 'mix2.wav'),
                    '-c:v', 'copy', '-af', 'loudnorm=I=-12:TP=-1.0:LRA=9', '-c:a', 'aac', '-b:a', '256k', '-ar',
                    '44100', '-shortest', '-movflags', '+faststart', out], check=True)
    print('done', out, len(frames), 'frames')


if __name__ == '__main__':
    main()
