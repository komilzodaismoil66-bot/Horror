"""«Крик»: the author's single recording, doubled in amplitude every stage, + destruction sound design.

No narrator, no other voices. Stage k plays the same recording with gain G1 * 2**k. Once the doubled level
passes digital full scale (from stage 7 on) the recording is driven into ever harder saturation, which keeps
it getting louder/denser without changing its speed or pitch. No loudness normalisation is applied afterwards,
so the build-up is preserved.
"""
import os
import subprocess
import numpy as np
from scipy.io import wavfile
from audio import SR, lp, hp, bp, norm, db, tt, reverb, IR_CITY, boom, crackle, growl, roar, step, whoosh, hiss
from audio3 import tunnel_rumble
from db_timeline import STAGES, STAGE, SHOUT_AT, TOTAL, ROOT, VOICE, SPD, INTER, SPACE_FROM, stage_start

N = int((TOTAL + 0.2) * SR)
rng = np.random.default_rng(12)
FULL_STAGE = 5          # stage index whose doubled level just reaches full scale (640 ДБ)


def noise(d):
    return rng.standard_normal(int(d * SR))


def load_voice():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', VOICE, '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.float64) / 32768


def stage_gain(k, v):
    g_full = 0.89 / np.max(np.abs(v))
    return g_full * 2.0 ** (k - FULL_STAGE)


def voice_stage(v, k):
    g = stage_gain(k, v)
    if g * np.max(np.abs(v)) <= 0.9:
        return v * g
    return np.tanh(v * g / 0.9) * 0.9             # beyond full scale: harder and harder saturation


def add(bus, t0, s, gain=1.0):
    if s.ndim == 1:
        s = np.stack([s, s], 1)
    i0 = int(t0 * SR)
    i1 = min(N, i0 + len(s))
    if i1 > i0:
        bus[i0:i1] += s[:i1 - i0] * gain


# ---------------------------------------------------------------- effects
def rustle(d, lo=2000, hi=7000, rate=3.0, seed=0):
    t = tt(d)
    x = bp(np.random.default_rng(seed).standard_normal(len(t)), lo, hi)
    am = 0.55 + 0.45 * np.sin(2 * np.pi * rate * t + np.sin(2 * np.pi * 0.7 * t) * 2)
    return norm(x * am * np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.8))


def wings(d, n=40, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    for i in range(n):
        t0 = r.uniform(0, d * 0.6)
        rate = r.uniform(9, 15)
        for k in range(int(r.uniform(6, 14))):
            i0 = int((t0 + k / rate) * SR)
            L = int(0.05 * SR)
            if i0 + L < len(out):
                out[i0:i0 + L] += bp(r.standard_normal(L), 300, 3000) * np.hanning(L) * r.uniform(0.3, 1)
    return norm(out)


def chirps(d, n=14, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    for i in range(n):
        t0 = r.uniform(0, d - 0.3)
        L = int(r.uniform(0.06, 0.14) * SR)
        f = np.linspace(r.uniform(2500, 3500), r.uniform(3800, 5200), L)
        c = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(L)
        i0 = int(t0 * SR)
        out[i0:i0 + L] += c * r.uniform(0.3, 1)
    return norm(out)


def creaks(d, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    for i in range(6):
        t0 = r.uniform(0, d - 1)
        L = int(r.uniform(0.4, 0.9) * SR)
        tl = np.arange(L) / SR
        f = r.uniform(90, 160) * (1 + 0.3 * np.sin(2 * np.pi * 2 * tl))
        pulses = (np.sin(2 * np.pi * np.cumsum(f / 4) / SR) > 0.95).astype(float)
        c = bp(pulses + 0.05 * r.standard_normal(L), 200, 2000) * np.hanning(L)
        i0 = int(t0 * SR)
        out[i0:i0 + L] += c
    return norm(out)


def crack_snaps(d, n=30, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    for i in range(n):
        t0 = r.uniform(0, d - 0.2) ** 1.3 / d ** 0.3
        L = int(r.uniform(0.03, 0.12) * SR)
        s = hp(r.standard_normal(L), r.uniform(600, 2500)) * np.exp(-np.arange(L) / (L / 4))
        i0 = int(t0 * SR)
        out[i0:i0 + L] += s * r.uniform(0.3, 1)
    return norm(out)


def stampede(d, rate=7, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    for i in range(int(d * rate)):
        i0 = int((i / rate + r.uniform(0, 0.08)) * SR)
        s = step(True, int(r.integers(1e6)))
        out[i0:i0 + len(s)] += s[:max(0, len(out) - i0)] * r.uniform(0.5, 1)
    return norm(lp(out, 900))


def rockslide(d, seed=0):
    r = np.random.default_rng(seed)
    t = tt(d)
    base = lp(r.standard_normal(len(t)), 500) * np.minimum(1, t / 0.5)
    out = norm(base) * 0.6
    for i in range(80):
        i0 = int(r.uniform(0, d - 0.3) * SR)
        L = int(r.uniform(0.05, 0.25) * SR)
        out[i0:i0 + L] += bp(r.standard_normal(L), 150, 3000) * np.exp(-np.arange(L) / (L / 5)) * r.uniform(0.2, 0.8)
    return norm(out)


def sub_vibration(d, f=38):
    t = tt(d)
    return norm(np.sin(2 * np.pi * f * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * t)) * np.minimum(1, t / 0.1) *
                np.minimum(1, (d - t) / 0.6))


def swell(d):
    t = tt(d)
    x = noise(d)
    out = np.zeros_like(x)
    seg = 2048
    for i in range(0, len(x), seg):
        f = 200 + 6000 * (i / len(x)) ** 2
        out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], f * 0.6, min(f * 1.6, 20000))[-len(x[i:i + seg]):]
    return norm(out * (t / d) ** 2)


def stage_fx(k):
    """(effects array (mono), level) for stage k, starting at the shout."""
    d = 8.2 - 0.55                       # effects were designed for the slower cut; events now come SPD x sooner
    fx = np.zeros(int(d * SR))

    def put(t0, s, g):
        i0 = int(t0 / SPD * SR)
        s = s[:max(0, len(fx) - i0)]
        fx[i0:i0 + len(s)] += s * g
    if k == 0:
        put(0.2, rustle(4.0, 3000, 8000, 2, 1), 0.5)
    if k == 1:
        put(0.1, rustle(6.0, 1500, 7000, 4, 2), 0.8)
    if k == 2:
        put(0.1, rustle(4, 1500, 6000, 5, 3), 0.4)
        put(0.15, wings(4.0, 40, 4), 0.9)
        put(0.4, chirps(4.0, 18, 5), 0.5)
    if k == 3:
        put(0.0, rustle(7.0, 800, 6000, 9, 6), 0.9)
        put(0.2, creaks(6.5, 7), 0.6)
        put(0.0, norm(lp(noise(6.0), 120)) * np.exp(-tt(6.0) * 0.4), 0.6)
    if k == 4:
        put(0.0, crack_snaps(4.0, 40, 8), 0.9)
        put(0.0, boom(3.0, 70), 0.8)
        put(0.0, tunnel_rumble(7.0, 9) * np.exp(-tt(7.0) * 0.3), 0.7)
    if k == 5:
        put(0.2, stampede(7.0, 9, 10), 0.9)
        put(0.4, roar(1.8), 0.7)
        put(2.0, growl(2.0, 60, 30, 900, 11), 0.5)
        put(3.4, roar(1.4), 0.5)
        put(0.0, tunnel_rumble(7.4, 12), 0.6)
    if k == 6:
        put(0.0, boom(4.0, 50), 1.0)
        put(0.3, rockslide(6.5, 13), 0.9)
        put(1.5, boom(3.0, 40), 0.7)
        put(0.0, tunnel_rumble(7.4, 14), 0.8)
    if k == 7:
        put(0.0, boom(3.0, 45), 0.9)
        put(0.5, crackle(7.0, 60, 15), 1.0)
        put(1.5, hiss(5.5, 16), 0.6)
        put(0.0, tunnel_rumble(7.4, 17), 0.8)
    if k == 8:
        put(0.0, boom(4.0, 40), 1.0)
        put(0.4, crack_snaps(3.0, 60, 18), 0.8)
        put(2.6, boom(4.0, 35), 1.0)
        put(2.6, whoosh(2.5, 2000, 200, 19), 0.7)
        put(0.0, tunnel_rumble(7.4, 20), 0.9)
    if k == 9:
        put(0.0, boom(4.0, 38), 1.0)
        put(0.1, whoosh(5.0, 100, 4000, 21), 0.9)
        put(1.5, boom(2.5, 60), 0.6)
        put(3.0, boom(2.5, 60), 0.6)
        put(0.0, sub_vibration(7.4, 34), 0.8)
    if k == 10:
        put(0.0, boom(4.0, 35), 1.0)
        put(0.2, swell(5.6), 1.0)
        put(0.0, sub_vibration(5.8, 30), 1.0)
        put(5.6, boom(3.0, 30), 1.0)
        put(5.6, norm(noise(1.8)) * np.exp(-tt(1.8) * 2.5), 0.8)
    if 3 <= k < 10:
        put(0.0, sub_vibration(2.2, 40), 0.5)
    return norm(fx) if np.max(np.abs(fx)) > 0 else fx


def main():
    v = load_voice()
    voice = np.zeros((N, 2))
    sfx = np.zeros((N, 2))
    for k in range(len(STAGES)):
        t0 = stage_start(k) + SHOUT_AT
        add(voice, t0, voice_stage(v, k))
        fx = stage_fx(k)
        if k == SPACE_FROM - 1:             # silence falls when the 'no sound in space' card appears
            cut = int((stage_start(SPACE_FROM) - INTER - t0) * SR)
            fx[cut:] *= 0
            fx[max(0, cut - 4000):cut] *= np.linspace(1, 0, min(4000, cut))
        lvl = min(1.0, 0.05 * 1.75 ** k)          # destruction grows with every stage too
        fx = reverb(fx, IR_CITY, 0.25 + 0.03 * k)[:len(fx)]
        add(sfx, t0, fx * lvl * 0.8)
    # keep the voice on top: duck the effects a little while it sounds
    env = np.convolve(np.abs(voice).max(1), np.ones(2000) / 2000, 'same')
    env = env / (env.max() + 1e-9)
    sfx *= (1 - 0.35 * env)[:, None]
    # the card: real space is silent; a soft swell leads into the 'imagined' sound
    t_card = stage_start(SPACE_FROM) - INTER
    add(sfx, t_card + INTER - 1.0, swell(1.0) * 0.25, 1.0)
    mix = voice + sfx
    i0, i1 = int(t_card * SR), int((t_card + INTER - 1.0) * SR)
    mix[i0:i1] *= 0.0
    mix = np.tanh(mix * 1.05) / np.tanh(1.05)              # soft safety limiter, no normalisation
    mix = np.clip(mix, -0.98, 0.98)
    fo = int((TOTAL - 0.4) * SR)
    mix[fo:] *= np.linspace(1, 0, N - fo)[:, None]
    out = os.path.join(ROOT, 'build', 'db')
    os.makedirs(out, exist_ok=True)
    wavfile.write(os.path.join(out, 'mix.wav'), SR, (mix * 32767).astype(np.int16))
    for k in range(len(STAGES)):
        seg = voice[int((stage_start(k) + SHOUT_AT) * SR):int((stage_start(k) + SHOUT_AT + 1.8) * SR)]
        pk = 20 * np.log10(np.max(np.abs(seg)) + 1e-9)
        rms = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
        print(f'{STAGES[k][0]:>6} ДБ: gain x{stage_gain(k, v):8.3f}  voice peak {pk:6.1f} dBFS  rms {rms:6.1f} dBFS')


if __name__ == '__main__':
    main()
