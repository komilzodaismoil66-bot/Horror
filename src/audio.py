"""Procedural sound design + voice mix -> build/mix.wav"""
import os
import subprocess
import numpy as np
from scipy import signal
from scipy.io import wavfile
from timeline import T, OFF, DUR, TOTAL, ROOT

SR = 44100
N = int((TOTAL + 0.5) * SR)
rng = np.random.default_rng(1)


def tt(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return rng.standard_normal(int(d * SR))


def lp(x, f, o=2):
    b, a = signal.butter(o, min(f, SR / 2 - 100) / (SR / 2), 'low')
    return signal.lfilter(b, a, x)


def hp(x, f, o=2):
    b, a = signal.butter(o, f / (SR / 2), 'high')
    return signal.lfilter(b, a, x)


def bp(x, f1, f2, o=2):
    b, a = signal.butter(o, [f1 / (SR / 2), min(f2, SR / 2 - 100) / (SR / 2)], 'band')
    return signal.lfilter(b, a, x)


def env_ad(n, a, d, curve=4.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) * curve / max(d, 1e-3))
    return e


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def ir(rt=1.5, pre=0.01, seed=0, bright=4000):
    r = np.random.default_rng(seed)
    n = int(rt * SR)
    t = np.arange(n) / SR
    e = np.exp(-6.9 * t / rt)
    L = lp(r.standard_normal(n) * e, bright)
    R = lp(r.standard_normal(n) * e, bright)
    pad = np.zeros(int(pre * SR))
    L = np.concatenate([pad, L])
    R = np.concatenate([pad, R])
    return L / np.sqrt(np.sum(L ** 2)), R / np.sqrt(np.sum(R ** 2))


IR_STAIR = ir(2.2, 0.02, 1, 3000)
IR_ROOM = ir(0.6, 0.005, 2, 5000)
IR_CITY = ir(3.0, 0.04, 3, 2500)


def reverb(x, irr, wet=0.4):
    L = signal.fftconvolve(x, irr[0])[:len(x) + len(irr[0])]
    R = signal.fftconvolve(x, irr[1])[:len(x) + len(irr[1])]
    n = len(L)
    dry = np.zeros(n)
    dry[:len(x)] = x
    return np.stack([dry * (1 - wet) + L * wet * 3, dry * (1 - wet) + R * wet * 3], 1)


class Bus:
    def __init__(self):
        self.x = np.zeros((N, 2))

    def add(self, t0, s, gain=1.0, pan=0.0):
        if s.ndim == 1:
            l = np.sqrt(0.5 * (1 - pan))
            r = np.sqrt(0.5 * (1 + pan))
            s = np.stack([s * l * 1.414, s * r * 1.414], 1)
        i0 = int(t0 * SR)
        if i0 < 0:
            s = s[-i0:]
            i0 = 0
        i1 = min(N, i0 + len(s))
        if i1 <= i0:
            return
        self.x[i0:i1] += s[:i1 - i0] * gain


SFX = Bus()


def db(v):
    return 10 ** (v / 20)


# ---------------------------------------------------------------- sound generators
def boom(d=3.0, f0=70):
    n = int(d * SR)
    t = tt(d)
    sub = np.sin(2 * np.pi * np.cumsum(np.linspace(f0, 28, n)) / SR) * np.exp(-t * 1.6)
    rum = lp(noise(d), 180, 4) * np.exp(-t * 1.2)
    crack = hp(noise(d), 1500) * np.exp(-t * 14) * 0.4
    return norm(sub * 0.9 + norm(rum) * 0.8 + crack)


def crackle(d, density=25, seed=0):
    r = np.random.default_rng(seed)
    n = int(d * SR)
    out = lp(np.cumsum(r.standard_normal(n)) * 0.002, 400) * 0.6     # low roar
    out = norm(hp(out, 30)) * 0.35
    k = int(d * density)
    for _ in range(k):
        i = r.integers(0, n - 2000)
        L = r.integers(150, 1200)
        burst = hp(r.standard_normal(L), r.uniform(800, 3000)) * np.exp(-np.arange(L) / (L / 5))
        out[i:i + L] += burst * r.uniform(0.15, 0.6)
    return out


def siren(d):
    t = tt(d)
    f = 720 + 320 * np.sin(2 * np.pi * 0.22 * t)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    return lp(s, 2000) * np.minimum(1, t / 1.5) * np.minimum(1, (d - t) / 1.5)


def growl(d, f0=48, rough=28, bright=500, seed=0):
    r = np.random.default_rng(seed)
    t = tt(d)
    n = len(t)
    am = 0.55 + 0.45 * np.sin(2 * np.pi * (rough + 4 * np.sin(2 * np.pi * 0.7 * t)) * t)
    nz = lp(r.standard_normal(n), bright, 4) * am
    fm = f0 * (1 + 0.08 * np.sin(2 * np.pi * 3.3 * t) + 0.05 * r.standard_normal(n).cumsum() / np.sqrt(n))
    ph = 2 * np.pi * np.cumsum(fm) / SR
    saw = signal.sawtooth(ph) * am
    s = norm(nz) * 0.7 + lp(saw, 900) * 0.5
    s = np.tanh(s * 2.5)
    e = np.minimum(1, t / 0.15) * np.minimum(1, (d - t) / 0.3)
    return norm(s * e)


def hiss(d, seed=0):
    t = tt(d)
    s = bp(np.random.default_rng(seed).standard_normal(len(t)), 2500, 9000) * np.minimum(1, t / 0.2) * \
        np.minimum(1, (d - t) / 0.4)
    return norm(s)


def roar(d):
    t = tt(d)
    g = growl(d, f0=70, rough=36, bright=1400, seed=4)
    rise = 0.4 + 0.6 * np.minimum(1, t / (d * 0.5))
    return norm(np.tanh(g * rise * 2.0) + hiss(d, 5) * 0.25)


def scream(d, f_lo=380, f_hi=560, seed=0, cut=None):
    r = np.random.default_rng(seed)
    t = tt(d)
    n = len(t)
    contour = f_lo + (f_hi - f_lo) * np.sin(np.pi * np.minimum(1, t / (d * 0.8))) ** 0.6
    vib = 1 + 0.025 * np.sin(2 * np.pi * 6.2 * t) + 0.01 * lp(r.standard_normal(n), 20)
    ph = 2 * np.pi * np.cumsum(contour * vib) / SR
    src = signal.sawtooth(ph) + 0.15 * r.standard_normal(n)
    out = 0
    for f, bw, g in ((850, 120, 1.0), (1250, 140, 0.8), (2800, 260, 0.45), (3500, 300, 0.25)):
        out = out + bp(src, f - bw, f + bw) * g
    e = np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.25)
    if cut is not None:
        e[int(cut * SR):] = 0
    return norm(np.tanh(norm(out) * 1.5) * e)


def heartbeat(n_beats, bpm=90):
    period = 60 / bpm
    out = np.zeros(int((n_beats * period + 1) * SR))
    for i in range(n_beats):
        for off, g in ((0, 1.0), (0.22, 0.7)):
            i0 = int((i * period + off) * SR)
            L = int(0.25 * SR)
            t = np.arange(L) / SR
            th = np.sin(2 * np.pi * 52 * t) * np.exp(-t * 22) + lp(rng.standard_normal(L), 120) * np.exp(-t * 30) * 0.5
            out[i0:i0 + L] += th * g
    return norm(out)


def step(heavy=False, seed=0):
    r = np.random.default_rng(seed)
    d = 0.35 if heavy else 0.12
    t = tt(d)
    if heavy:
        s = np.sin(2 * np.pi * 42 * t) * np.exp(-t * 9) + lp(r.standard_normal(len(t)), 250) * np.exp(-t * 12) * 0.8
    else:
        s = bp(r.standard_normal(len(t)), 200, 2400) * np.exp(-t * 45) + np.sin(2 * np.pi * 95 * t) * np.exp(
            -t * 40) * 0.6
    return norm(s)


def clang(d=3.5):
    t = tt(d)
    s = 0
    for f, dec, g in ((523, 1.2, 1.0), (1347, 1.6, 0.7), (2213, 2.2, 0.55), (3170, 2.8, 0.4), (4410, 3.5, 0.3),
                      (887, 1.4, 0.5), (6120, 5, 0.2)):
        s = s + np.sin(2 * np.pi * f * t * (1 + 0.002 * np.sin(2 * np.pi * 5 * t))) * np.exp(-t * dec) * g
    imp = hp(noise(d), 1200) * np.exp(-t * 30)
    thud = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 12)
    # a few bounces
    out = norm(s) * 0.8 + imp * 0.5 + thud * 0.6
    for k, (dt_, g) in enumerate(((0.22, 0.45), (0.38, 0.25))):
        i = int(dt_ * SR)
        out[i:] += (norm(s) * 0.5 + imp * 0.3)[:len(out) - i] * g
    return norm(out)


def whoosh(d=0.6, f0=300, f1=3000, seed=0):
    t = tt(d)
    x = np.random.default_rng(seed).standard_normal(len(t))
    out = np.zeros_like(x)
    seg = 512
    for i in range(0, len(x), seg):
        f = f0 + (f1 - f0) * (i / len(x))
        out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], f * 0.7, f * 1.3)[-len(x[i:i + seg]):]
    e = np.sin(np.pi * np.minimum(1, t / d)) ** 2
    return norm(out * e)


def creak(d=1.2):
    t = tt(d)
    f = 180 + 60 * np.sin(2 * np.pi * 0.8 * t)
    pulses = (signal.sawtooth(2 * np.pi * np.cumsum(f / 6) / SR) > 0.9).astype(float)
    s = bp(pulses + 0.1 * noise(d), 300, 2500) * np.sin(np.pi * t / d)
    return norm(s)


def pop():
    t = tt(0.15)
    f = np.linspace(500, 1200, len(t))
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30))


def drone(d):
    t = tt(d)
    s = 0
    for f, g in ((41.2, 1.0), (41.6, 0.8), (61.7, 0.4), (43.6, 0.35), (164.8, 0.08), (174.6, 0.06)):
        s = s + np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * g
    s = s * (0.75 + 0.25 * np.sin(2 * np.pi * 0.05 * t))
    nz = lp(noise(d), 300) * 0.6 * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t + 1))
    return norm(s + norm(nz) * 0.4)


def tinnitus(d=2.0):
    t = tt(d)
    return np.sin(2 * np.pi * 3800 * t) * np.exp(-t * 1.8) * np.minimum(1, t / 0.05)


def scrabble(d, rate=14, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    k = int(d * rate)
    for i in range(k):
        i0 = int((i / rate + r.uniform(0, 0.03)) * SR)
        s = step(heavy=(i % 4 == 0), seed=int(r.integers(1e6))) * (1.0 if i % 4 == 0 else 0.5)
        clk = hp(r.standard_normal(600), 3000) * np.exp(-np.arange(600) / 80) * 0.6
        out[i0:i0 + len(s)] += s[:len(out) - i0]
        out[i0:i0 + 600] += clk[:max(0, min(600, len(out) - i0))]
    return norm(out)


def stinger(d=2.5):
    t = tt(d)
    b = boom(d, 55) * 0.9
    hi = 0
    for f in (1760, 1864, 2489):
        hi = hi + signal.sawtooth(2 * np.pi * f * t * (1 + 0.004 * np.sin(2 * np.pi * 7 * t)))
    hi = bp(hi, 1200, 5000) * np.exp(-t * 2.2) * np.minimum(1, t / 0.02)
    return norm(b + norm(hi) * 0.35)


# ---------------------------------------------------------------- arrangement
def build():
    E = SFX
    t_end = OFF[8] + DUR[8]
    # drone bed
    E.add(0, drone(TOTAL), db(-24))
    E.add(OFF[5], drone(OFF[8] - OFF[5]) , db(-26))

    # 1. booms & waking
    E.add(0.25, reverb(boom(4, 80), IR_CITY, 0.3), db(-6))
    tb = T(1, 'грохота')
    E.add(tb - 0.1, reverb(boom(4, 90), IR_CITY, 0.3), db(-4))
    E.add(tb + 0.15, reverb(pop() * 0, IR_ROOM), 0)
    # fire through the window / city
    E.add(T(1, 'ты', 1), crackle(5, 15, 1), db(-24))
    E.add(T(1, 'весь') - 0.2, crackle(OFF[2] - T(1, 'весь') + 0.5, 30, 2), db(-15))
    E.add(T(1, 'весь'), reverb(siren(9) * 0.6, IR_CITY, 0.6), db(-26), pan=-0.4)
    tc = T(1, 'рушатся') - 0.25
    E.add(tc + 0.2, reverb(boom(4, 50), IR_CITY, 0.4), db(-7))
    E.add(tc + 1.4, reverb(lp(noise(3), 600) * np.exp(-tt(3) * 1.4), IR_CITY, 0.4), db(-12))
    # distant people screams in panic
    E.add(T(1, 'люди') - 0.8, reverb(scream(1.1, 420, 600, 3), IR_CITY, 0.7), db(-26), pan=0.5)
    E.add(T(1, 'люди') - 0.2, reverb(scream(0.9, 500, 700, 4), IR_CITY, 0.7), db(-28), pan=-0.3)
    # giants: heavy footsteps + growl in smoke
    t0 = T(1, 'но')
    for i in range(4):
        E.add(t0 + 0.3 + i * 1.56, reverb(step(True, i), IR_CITY, 0.5), db(-8))
    E.add(t0 + 1.0, reverb(growl(2.5, 40, 22, 400, 1), IR_CITY, 0.5), db(-18))

    # 2. anatomy
    E.add(OFF[2] - 0.35, stinger(3), db(-10))
    E.add(OFF[2] + 1.0, growl(3.0, 38, 20, 300, 2), db(-22))
    tp = T(2, 'пасть') - 0.1
    E.add(tp, growl(1.6, 60, 34, 1200, 3), db(-12))
    E.add(tp, hiss(1.6, 1), db(-20))
    E.add(T(2, 'рядами'), whoosh(0.8, 200, 1200, 1), db(-18))
    th = T(2, 'слухом') - 0.2
    E.add(th, reverb(step(False, 3), IR_CITY, 0.6), db(-14), pan=0.7)
    E.add(th + 0.5, whoosh(0.3, 400, 2500, 2), db(-16))
    E.add(th + 0.5, growl(1.0, 55, 30, 700, 5), db(-16))
    tw = T(2, 'шопот')
    E.add(tw, hiss(0.9, 3) * 0.5, db(-26))
    ta = T(2, 'внимание')
    E.add(ta, stinger(2.5), db(-12))
    E.add(ta + 0.2, growl(1.8, 45, 24, 500, 6), db(-16))

    # 3. packing
    E.add(T(3, 'рюкзак') - 0.1, pop(), db(-16))
    for w in ('воду', 'еду', 'аптечку', 'фонарик'):
        E.add(T(3, w), pop(), db(-14))
        E.add(T(3, w) + 0.38, whoosh(0.35, 500, 2500, 3), db(-20))
    E.add(T(3, 'фонарик', end=True) + 0.2, bp(noise(0.5), 2000, 7000) * np.sin(np.pi * tt(0.5) / 0.5), db(-22))
    tq = T(3, 'затем') - 0.15
    E.add(tq + 0.05, reverb(creak(1.2), IR_STAIR, 0.4), db(-20))
    for i in range(6):
        E.add(tq + 0.6 + i * 0.5, reverb(step(False, 10 + i) * 0.4, IR_STAIR, 0.5), db(-24))

    # 4. scream in the stairwell
    tk = T(4, 'крик')
    E.add(tk + 0.2, stinger(2), db(-14))
    E.add(tk + 0.45, reverb(scream(1.4, 360, 520, 7), IR_STAIR, 0.6), db(-10), pan=-0.4)

    # 5. man, monster, grab
    E.add(OFF[5] + 1.9, reverb(scream(0.7, 300, 420, 8) * 0.6, IR_STAIR, 0.5), db(-24), pan=-0.3)
    tdk = T(5, 'темноты')
    E.add(tdk, reverb(growl(2.5, 40, 22, 350, 7), IR_STAIR, 0.4), db(-16))
    E.add(T(5, 'появляется'), stinger(3), db(-12))
    tg = T(5, 'хватает')
    tcut = T(5, 'резко') - 0.05
    E.add(tg - 0.1, whoosh(0.4, 300, 2500, 4), db(-12))
    E.add(tg, boom(1.0, 90) * 0.6, db(-14))
    E.add(tg + 0.05, reverb(scream(tcut - tg, 420, 640, 9), IR_STAIR, 0.45)[:int((tcut - tg) * SR)], db(-16),
          pan=-0.2)
    E.add(T(5, 'утаскивает'), whoosh(0.7, 2000, 200, 5), db(-10))
    E.add(T(5, 'утаскивает'), reverb(roar(1.2), IR_STAIR, 0.4), db(-14))
    E.add(tcut, tinnitus(2.2), db(-34))
    E.add(tcut + 0.4, heartbeat(4, 70), db(-14))

    # 6. run, echo, turn
    t6 = OFF[6]
    for i in range(int((T(6, 'монстр') - t6) / 0.27)):
        E.add(t6 + 0.15 + i * 0.27, reverb(step(False, 30 + i), IR_STAIR, 0.55), db(-14 if i % 2 else -12),
              pan=0.2 * (-1) ** i)
    ts = T(6, 'резко') + 0.1
    E.add(ts - 0.05, whoosh(0.25, 500, 4000, 6), db(-10))
    E.add(ts, stinger(2.2), db(-9))
    E.add(T(6, 'он') - 0.1, growl(1.6, 50, 26, 600, 8), db(-14))
    E.add(T(6, 'тебя'), reverb(roar(1.2), IR_STAIR, 0.4), db(-10))

    # 7. climb, hide, rebar
    t7 = OFF[7] - 0.3
    E.add(t7, reverb(scrabble(T(7, 'ты') - t7, 13, 1), IR_STAIR, 0.45), db(-11))
    E.add(t7 + 0.2, reverb(growl(2.8, 45, 30, 700, 9), IR_STAIR, 0.4), db(-17))
    E.add(T(7, 'прячешься') + 0.2, heartbeat(11, 120), db(-13))
    E.add(T(7, 'задеваешь'), bp(noise(0.5), 600, 3000) * np.exp(-tt(0.5) * 6) * 0.5, db(-18))
    thit = T(7, 'грохотом') - 0.05
    E.add(thit, reverb(clang(3.5), IR_STAIR, 0.55), db(-3))
    E.add(thit + 1.0, reverb(growl(1.6, 52, 30, 900, 10), IR_STAIR, 0.5), db(-14))

    # 8. knows, lunge, escape
    E.add(OFF[8] - 0.3, reverb(scrabble(2.6, 16, 2), IR_STAIR, 0.45), db(-14))
    tl = T(8, 'он') - 0.1
    E.add(tl, roar(1.5), db(-6))
    E.add(tl + 0.1, whoosh(1.2, 200, 3000, 7), db(-12))
    tesc = T(8, 'выскакиваешь') - 0.35
    E.add(tesc - 0.05, boom(1.2, 110) * 0.8, db(-9))                      # door bursts
    E.add(tesc + 0.3, whoosh(0.4, 600, 3000, 8), db(-12))
    E.add(tesc + 0.45, reverb(boom(1.0, 90), IR_CITY, 0.3), db(-12))       # claws smash the frame
    E.add(tesc + 0.5, reverb(roar(1.5), IR_CITY, 0.5), db(-12))
    E.add(T(8, 'ты', 1) - 0.1, crackle(t_end - T(8, 'ты', 1) + 3, 30, 5), db(-16))
    E.add(T(8, 'ты', 1), reverb(siren(8) * 0.6, IR_CITY, 0.6), db(-28), pan=0.5)
    for i in range(int((t_end - tesc) / 0.3)):
        E.add(tesc + 0.1 + i * 0.3, step(False, 60 + i), db(-18 - i * 0.6))
    # outro
    E.add(t_end + 1.2, reverb(stinger(4), IR_CITY, 0.4), db(-9))

    # fade out
    fo = int((TOTAL - 1.2) * SR)
    ramp = np.linspace(1, 0, N - fo)[:, None]
    E.x[fo:] *= ramp


def load_voice():
    V = np.zeros((N, 2))
    for i in range(1, 9):
        p = os.path.join(ROOT, 'audio', f'part{i}.mp3')
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'],
                             capture_output=True).stdout
        a = np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.float64) / 32768
        i0 = int(OFF[i] * SR)
        V[i0:i0 + len(a)] += a[:N - i0]
    return V


def main():
    build()
    V = load_voice()
    # duck sfx under the voice
    env = np.abs(V).max(1)
    win = int(0.08 * SR)
    env = np.convolve(env, np.ones(win) / win, 'same')
    env = np.clip(env / (np.percentile(env[env > 0.01], 90) + 1e-6), 0, 1)
    duck = 1 - 0.6 * env
    S = SFX.x * duck[:, None] * db(-6)
    S = np.tanh(S * 1.2) / 1.2
    mix = V * 1.0 + S * 0.9
    mix = mix / max(1.0, np.max(np.abs(mix)) / 0.98)
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    wavfile.write(os.path.join(ROOT, 'build', 'mix.wav'), SR, (mix * 32767).astype(np.int16))
    wavfile.write(os.path.join(ROOT, 'build', 'sfx.wav'), SR, (np.clip(S, -1, 1) * 32767).astype(np.int16))
    print('mix written', N / SR)


if __name__ == '__main__':
    main()
