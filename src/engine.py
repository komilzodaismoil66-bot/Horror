"""Core drawing helpers: colours, easing, noise, shapes, camera, lighting, post FX."""
import math
import random
import cairo
import numpy as np

W, H = 1080, 1920
FPS = 30


# ---------------------------------------------------------------- colours
def hexc(h, a=1.0):
    h = h.lstrip('#')
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(4))


def mul(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, c[3])


def alpha(c, a):
    return (c[0], c[1], c[2], c[3] * a)


def src(ctx, c):
    if len(c) == 3:
        ctx.set_source_rgb(*c)
    else:
        ctx.set_source_rgba(*c)


# ---------------------------------------------------------------- maths
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def seg(t, a, b):
    """Normalised progress of t inside [a, b]."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return clamp((t - a) / (b - a))


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_in(t):
    t = clamp(t)
    return t * t * t


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_io(t):
    t = clamp(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def back_out(t, s=1.70158):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def elastic_out(t):
    t = clamp(t)
    if t in (0, 1):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


_perm = list(range(512))
random.Random(7).shuffle(_perm)
_vals = [random.Random(i * 31 + 5).uniform(-1, 1) for i in range(512)]


def noise(x, seed=0):
    """Smooth 1D value noise in [-1, 1]."""
    x += seed * 17.13
    i = math.floor(x)
    f = x - i
    a = _vals[_perm[int(i) & 511]]
    b = _vals[_perm[int(i + 1) & 511]]
    u = f * f * (3 - 2 * f)
    return a + (b - a) * u


def fbm(x, seed=0, oct=3):
    v, amp, fr = 0.0, 0.5, 1.0
    for o in range(oct):
        v += noise(x * fr, seed + o * 3.3) * amp
        fr *= 2.1
        amp *= 0.5
    return v * 1.6


def jerk(t, rate=3.0, seed=0):
    """Step-like twitching motion (creepy head ticks)."""
    k = math.floor(t * rate)
    f = t * rate - k
    a = noise(k * 1.7, seed)
    b = noise((k + 1) * 1.7, seed)
    s = clamp(f * 6)          # snap quickly, then hold
    return a + (b - a) * smooth(s)


def rot(p, ang, o=(0, 0)):
    c, s = math.cos(ang), math.sin(ang)
    x, y = p[0] - o[0], p[1] - o[1]
    return (o[0] + x * c - y * s, o[1] + x * s + y * c)


def ik2(a, target, l1, l2, bend=1):
    """Two-bone IK. Returns joint position. bend=+1/-1 picks the side."""
    dx, dy = target[0] - a[0], target[1] - a[1]
    d = math.hypot(dx, dy)
    d = max(1e-3, min(d, l1 + l2 - 1e-3))
    base = math.atan2(dy, dx)
    cosv = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    ang = math.acos(clamp(cosv, -1, 1))
    t = base - ang * bend
    return (a[0] + l1 * math.cos(t), a[1] + l1 * math.sin(t))


def clamp_reach(a, target, reach):
    dx, dy = target[0] - a[0], target[1] - a[1]
    d = math.hypot(dx, dy)
    if d <= reach:
        return target
    return (a[0] + dx / d * reach, a[1] + dy / d * reach)


# ---------------------------------------------------------------- shapes
def poly(ctx, pts, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()


def fill_poly(ctx, pts, c):
    poly(ctx, pts)
    src(ctx, c)
    ctx.fill()


def rect(ctx, x, y, w, h, c):
    ctx.rectangle(x, y, w, h)
    src(ctx, c)
    ctx.fill()


def rrect_path(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()


def rrect(ctx, x, y, w, h, r, c):
    rrect_path(ctx, x, y, w, h, r)
    src(ctx, c)
    ctx.fill()


def circle(ctx, x, y, r, c):
    ctx.new_sub_path()
    ctx.arc(x, y, max(r, 0.01), 0, 2 * math.pi)
    src(ctx, c)
    ctx.fill()


def ellipse_path(ctx, x, y, rx, ry, ang=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    ctx.scale(max(rx, 0.01), max(ry, 0.01))
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def ellipse(ctx, x, y, rx, ry, c, ang=0.0):
    ellipse_path(ctx, x, y, rx, ry, ang)
    src(ctx, c)
    ctx.fill()


def line(ctx, a, b, w, c, cap=cairo.LINE_CAP_ROUND):
    ctx.move_to(*a)
    ctx.line_to(*b)
    ctx.set_line_width(w)
    ctx.set_line_cap(cap)
    src(ctx, c)
    ctx.stroke()


def polyline(ctx, pts, w, c, cap=cairo.LINE_CAP_ROUND, join=cairo.LINE_JOIN_ROUND):
    poly(ctx, pts, close=False)
    ctx.set_line_width(w)
    ctx.set_line_cap(cap)
    ctx.set_line_join(join)
    src(ctx, c)
    ctx.stroke()


def taper(ctx, a, b, w1, w2, c, round_ends=True):
    """Tapered limb segment between a and b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 1e-3
    nx, ny = -dy / d, dx / d
    pts = [(a[0] + nx * w1 / 2, a[1] + ny * w1 / 2), (b[0] + nx * w2 / 2, b[1] + ny * w2 / 2),
           (b[0] - nx * w2 / 2, b[1] - ny * w2 / 2), (a[0] - nx * w1 / 2, a[1] - ny * w1 / 2)]
    poly(ctx, pts)
    src(ctx, c)
    ctx.fill()
    if round_ends:
        circle(ctx, a[0], a[1], w1 / 2, c)
        circle(ctx, b[0], b[1], w2 / 2, c)


def radial(ctx, x, y, r, c, a0=1.0, op=None, r0=0.0):
    g = cairo.RadialGradient(x, y, r0, x, y, max(r, 1))
    g.add_color_stop_rgba(0, c[0], c[1], c[2], a0)
    g.add_color_stop_rgba(0.45, c[0], c[1], c[2], a0 * 0.35)
    g.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
    ctx.save()
    if op is not None:
        ctx.set_operator(op)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def glow(ctx, x, y, r, c, a0=0.6):
    radial(ctx, x, y, r, c, a0, cairo.OPERATOR_SCREEN)


def vgrad(ctx, x, y, w, h, stops):
    g = cairo.LinearGradient(0, y, 0, y + h)
    for off, c in stops:
        g.add_color_stop_rgba(off, *c)
    ctx.rectangle(x, y, w, h)
    ctx.set_source(g)
    ctx.fill()


def cone_path(ctx, x, y, ang, spread, length):
    a1, a2 = ang - spread, ang + spread
    ctx.move_to(x, y)
    ctx.line_to(x + math.cos(a1) * length, y + math.sin(a1) * length)
    ctx.arc(x, y, length, a1, a2)
    ctx.close_path()


# ---------------------------------------------------------------- camera
def camera(ctx, cx, cy, zoom=1.0, rot_=0.0, shake=0.0, t=0.0):
    sx = sy = 0.0
    if shake > 0:
        sx = (noise(t * 23, 1) * 0.7 + noise(t * 57, 2) * 0.3) * shake
        sy = (noise(t * 21, 3) * 0.7 + noise(t * 61, 4) * 0.3) * shake
    ctx.translate(W / 2 + sx, H / 2 + sy)
    if rot_ or shake:
        ctx.rotate(rot_ + noise(t * 13, 5) * shake * 0.0006)
    ctx.scale(zoom, zoom)
    ctx.translate(-cx, -cy)


class Darkness:
    """Darkness layer with light holes punched into it (flashlights, lamps)."""

    def __init__(self, ctx, amount=0.85, color=(0.01, 0.015, 0.04)):
        self.ctx = ctx
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        self.d = cairo.Context(self.surf)
        self.d.set_source_rgba(color[0], color[1], color[2], amount)
        self.d.paint()
        self.d.set_matrix(ctx.get_matrix())
        self.d.set_operator(cairo.OPERATOR_DEST_OUT)

    def hole(self, x, y, r, strength=1.0):
        g = cairo.RadialGradient(x, y, 0, x, y, r)
        g.add_color_stop_rgba(0, 0, 0, 0, strength)
        g.add_color_stop_rgba(0.5, 0, 0, 0, strength * 0.6)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        self.d.set_source(g)
        self.d.arc(x, y, r, 0, 2 * math.pi)
        self.d.fill()

    def cone(self, x, y, ang, spread, length, strength=1.0):
        g = cairo.RadialGradient(x, y, 0, x, y, length)
        g.add_color_stop_rgba(0, 0, 0, 0, strength)
        g.add_color_stop_rgba(0.6, 0, 0, 0, strength * 0.7)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        # soft edges: several widening cones (DEST_OUT compounds multiplicatively)
        for k, s in ((1.0, 0.75), (1.25, 0.45), (1.6, 0.3)):
            g = cairo.RadialGradient(x, y, 0, x, y, length)
            g.add_color_stop_rgba(0, 0, 0, 0, strength * s)
            g.add_color_stop_rgba(0.6, 0, 0, 0, strength * s * 0.7)
            g.add_color_stop_rgba(1, 0, 0, 0, 0)
            cone_path(self.d, x, y, ang, spread * k, length)
            self.d.set_source(g)
            self.d.fill()

    def apply(self):
        self.ctx.save()
        self.ctx.identity_matrix()
        self.ctx.set_source_surface(self.surf, 0, 0)
        self.ctx.paint()
        self.ctx.restore()


# ---------------------------------------------------------------- post FX
_grain = []
_vignette = None


def _init_post():
    global _vignette
    rng = np.random.default_rng(3)
    for i in range(6):
        n = rng.integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
        a = np.full_like(n, 255)
        arr = np.dstack([n, n, n, a]).astype(np.uint8)
        arr = np.ascontiguousarray(arr)
        s = cairo.ImageSurface.create_for_data(memoryview(bytearray(arr.tobytes())), cairo.FORMAT_ARGB32,
                                               W // 2, H // 2)
        _grain.append(s)
    _vignette = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(_vignette)
    g = cairo.RadialGradient(W / 2, H * 0.45, H * 0.22, W / 2, H * 0.45, H * 0.72)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(0.6, 0, 0, 0.02, 0.35)
    g.add_color_stop_rgba(1, 0, 0, 0.02, 0.92)
    c.set_source(g)
    c.paint()


def post(ctx, t, vignette=1.0, grain=0.07, tint=None):
    if _vignette is None:
        _init_post()
    ctx.save()
    ctx.identity_matrix()
    if tint is not None:
        ctx.set_source_rgba(*tint)
        ctx.paint()
    if vignette > 0:
        ctx.set_source_surface(_vignette, 0, 0)
        ctx.paint_with_alpha(vignette)
    if grain > 0:
        g = _grain[int(t * FPS) % len(_grain)]
        ctx.scale(2, 2)
        ctx.set_source_surface(g, 0, 0)
        ctx.get_source().set_filter(cairo.FILTER_FAST)
        ctx.set_operator(cairo.OPERATOR_OVERLAY)
        ctx.paint_with_alpha(grain)
    ctx.restore()


def fade(ctx, a, c=(0, 0, 0)):
    if a <= 0:
        return
    ctx.save()
    ctx.identity_matrix()
    ctx.set_source_rgba(c[0], c[1], c[2], clamp(a))
    ctx.paint()
    ctx.restore()


def flash(ctx, a, c=(1, 0.95, 0.85)):
    fade(ctx, a, c)


# ---------------------------------------------------------------- text
def text_path(ctx, s, x, y, size, font='Montserrat Black', anchor='center'):
    ctx.select_font_face(font)
    ctx.set_font_size(size)
    xb, yb, tw, th, xa, ya = ctx.text_extents(s)
    if anchor == 'center':
        x -= xa / 2
    elif anchor == 'right':
        x -= xa
    ctx.move_to(x, y)
    ctx.text_path(s)
    return xa


def text(ctx, s, x, y, size, c, font='Montserrat Black', anchor='center', outline=None, ow=0):
    ctx.save()
    text_path(ctx, s, x, y, size, font, anchor)
    if outline is not None:
        src(ctx, outline)
        ctx.set_line_width(ow)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
    src(ctx, c)
    ctx.fill()
    ctx.restore()


def text_width(ctx, s, size, font='Montserrat Black'):
    ctx.save()
    ctx.select_font_face(font)
    ctx.set_font_size(size)
    w = ctx.text_extents(s)[4]
    ctx.restore()
    return w
