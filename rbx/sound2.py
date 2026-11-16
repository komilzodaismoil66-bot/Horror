"""Original trailer-style score + fight sound design, synced to events2.json -> rbx/build/mix.wav"""
import json
import os
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
from audio import SR, lp, hp, bp, norm, reverb, IR_CITY, IR_STAIR, boom, whoosh, step

EV = json.load(open(os.path.join(HERE, 'events2.json')))
END = EV['cut']                   # last picture second
TOTAL = END + 3.0                 # + TO BE CONTINUED card
N = int(TOTAL * SR)
rng = np.random.default_rng(7)


def tt(d):
    return np.arange(int(d * SR)) / SR


def noise(d):
    return rng.standard_normal(int(d * SR))


def put(bus, t0, s, g=1.0):
    if s.ndim == 1:
        s = np.stack([s, s], 1)
    i0 = int(t0 * SR)
    i1 = min(N, i0 + len(s))
    if i1 > i0 and i0 >= 0:
        bus[i0:i1] += s[:i1 - i0] * g


def env_keys(keys):
    k = np.array(keys)
    return np.interp(np.arange(N) / SR, k[:, 0], k[:, 1])


# ---------------------------------------------------------------- instruments
def taiko(pitch=60, d=0.9):
    t = tt(d)
    f = pitch * (1 + 1.5 * np.exp(-t * 30))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)
    s += lp(rng.standard_normal(len(t)), 900) * np.exp(-t * 25) * 0.6
    return np.tanh(s * 1.8)


def snare(d=0.35):
    t = tt(d)
    return norm(bp(rng.standard_normal(len(t)), 1500, 8000) * np.exp(-t * 16) + np.sin(2 * np.pi * 200 * t) * np.exp(
        -t * 30) * 0.5)


def braam(d=3.0, root=36.7):
    t = tt(d)
    s = 0
    for mul, g in ((1, 1.0), (2, 0.7), (3.0, 0.35), (1.5, 0.5)):
        for det in (-0.006, 0, 0.006):
            s = s + signal.sawtooth(2 * np.pi * root * mul * (1 + det) * t) * g
    cut = 300 + 2500 * np.exp(-t * 2.0)
    out = np.zeros_like(s)
    seg = 2048
    for i in range(0, len(s), seg):
        out[i:i + seg] = lp(s[max(0, i - 4096):i + seg], float(cut[i]))[-len(s[i:i + seg]):]
    e = np.minimum(1, t / 0.04) * np.exp(-t * 0.9)
    return norm(np.tanh(out * e * 1.4))


def pad(freqs, d, cutoff=900):
    t = tt(d)
    s = 0
    for f in freqs:
        for det in (-0.005, 0.0, 0.005):
            s = s + signal.sawtooth(2 * np.pi * f * (1 + det) * t + rng.uniform(0, 6))
    return norm(lp(s, cutoff))


def ostinato(d, bpm, notes, gate=0.5):
    out = np.zeros(int(d * SR))
    step_t = 60 / bpm / 4
    k = 0
    while k * step_t < d:
        f = notes[k % len(notes)]
        L = int(step_t * gate * SR)
        tl = np.arange(L) / SR
        n = (signal.sawtooth(2 * np.pi * f * tl) + signal.sawtooth(2 * np.pi * f * 1.004 * tl)) * np.exp(-tl * 10)
        i0 = int(k * step_t * SR)
        out[i0:i0 + L] += n[:max(0, min(L, len(out) - i0))]
        k += 1
    return lp(out, 2500)


def drums(d, bpm, heavy=1.0):
    out = np.zeros(int(d * SR))
    beat = 60 / bpm
    pat = [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1]           # 16ths, trailer groove
    k = 0
    while k * beat / 4 < d:
        i0 = int(k * beat / 4 * SR)
        if pat[k % 16]:
            s = taiko(55 if k % 4 == 0 else 75) * (1.0 if k % 4 == 0 else 0.6) * heavy
            out[i0:i0 + len(s)] += s[:max(0, len(out) - i0)]
        if k % 8 == 4:
            s = snare() * 0.7
            out[i0:i0 + len(s)] += s[:max(0, len(out) - i0)]
        k += 1
    return out


def rain(d):
    x = noise(d)
    s = bp(x, 1500, 9000) * 0.6 + lp(x, 400) * 0.3
    drops = np.zeros_like(x)
    idx = rng.integers(0, len(x), int(d * 300))
    drops[idx] = rng.uniform(0.2, 1, len(idx))
    return norm(s + hp(drops, 2000) * 0.8)


def punch(size=1.0):
    t = tt(0.6)
    thump = np.sin(2 * np.pi * np.cumsum(70 + 160 * np.exp(-t * 40)) / SR) * np.exp(-t * 12)
    crack = hp(noise(0.6), 2500) * np.exp(-t * 60)
    body = bp(noise(0.6), 200, 1500) * np.exp(-t * 20)
    return norm(thump * 1.2 + crack * 0.6 + body * 0.5) * min(1.0, 0.55 + 0.25 * size)


def zap():
    t = tt(0.5)
    f = 3000 * np.exp(-t * 9) + 200
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    return norm(s + hp(noise(0.5), 4000) * np.exp(-t * 14) * 0.5)


def rattle(d=1.5):
    out = np.zeros(int(d * SR))
    for i in range(40):
        i0 = int(rng.uniform(0, d - 0.15) ** 1.5 / d ** 0.5 * SR)
        L = int(rng.uniform(0.03, 0.1) * SR)
        out[i0:i0 + L] += bp(rng.standard_normal(L), 400, 4000) * np.exp(-np.arange(L) / (L / 4)) * rng.uniform(0.3, 1)
    return norm(out)


def rumble(d):
    t = tt(d)
    return norm(lp(noise(d), 90, 4) * (0.6 + 0.4 * np.sin(2 * np.pi * 5 * t)))


def heartbeat(n, bpm):
    p = 60 / bpm
    out = np.zeros(int((n * p + 1) * SR))
    for i in range(n):
        for off, g in ((0, 1.0), (0.2, 0.65)):
            i0 = int((i * p + off) * SR)
            L = int(0.25 * SR)
            tl = np.arange(L) / SR
            out[i0:i0 + L] += np.sin(2 * np.pi * 50 * tl) * np.exp(-tl * 22) * g
    return norm(out)


def build():
    mus = np.zeros((N, 2))
    sfx = np.zeros((N, 2))
    T4, WAVE, CH = EV['boss_in'], EV['wave'], EV['charge']
    D1, D2 = 14.0, 40.6            # duel start, reinforcements
    S5 = 70.0
    o1 = [146.8, 146.8, 174.6, 146.8, 220.0, 146.8, 196.0, 174.6]
    o2 = [146.8, 220.0, 174.6, 146.8, 233.1, 220.0, 196.0, 174.6]
    o3 = [146.8, 155.6, 146.8, 220.0, 146.8, 155.6, 207.7, 196.0]
    # ---- score: meeting
    d = D1 - 0.05
    put(mus, 0.0, pad([55.0, 82.4, 110.0, 130.8], d, 500) * np.linspace(0.15, 1, int(d * SR)), 0.45)
    put(mus, 5.6, heartbeat(12, 92), 0.35)
    put(mus, 0.0, braam(4.0, 27.5), 0.35)
    put(mus, 12.9, whoosh(1.1, 200, 5000, 1), 0.5)
    # ---- duel
    put(mus, D1, braam(3.0, 36.7), 0.9)
    put(mus, D1, drums(D2 - D1, 120), 0.75)
    put(mus, D1, ostinato(27.0 - D1, 120, o1), 0.22)
    put(mus, 27.0, ostinato(D2 - 27.0, 120, o2), 0.24)
    for t, r, g in ((18.47, 41.2, 0.6), (20.78, 36.7, 0.7), (27.8, 32.7, 0.8), (31.0, 41.2, 0.6), (36.36, 36.7, 0.8),
                    (39.44, 32.7, 0.9)):
        put(mus, t, braam(2.5, r), g)
    put(mus, 21.0, pad([73.4, 110.0, 146.8, 174.6], D2 - 21.0, 1200), 0.16)
    # ---- reinforcements
    put(mus, D2, drums(T4 - D2, 120, 1.15), 0.8)
    put(mus, D2, ostinato(T4 - D2, 120, o3), 0.25)
    put(mus, D2, pad([73.4, 110.0, 146.8, 185.0, 220.0], T4 - D2, 1500), 0.2)
    for t, r, g in ((41.0, 36.7, 0.8), (46.78, 32.7, 0.9), (50.7, 41.2, 0.6)):
        put(mus, t, braam(2.5, r), g)
    # ---- the strongest: drums out, dread
    put(mus, T4, pad([36.7, 55.0, 73.4, 77.8], S5 - T4, 400), 0.6)
    put(mus, T4 + 2.35, braam(4.0, 30.9), 1.0)
    put(mus, 60.4, braam(4.0, 27.5), 0.9)
    put(mus, 66.4, braam(3.5, 30.9), 0.8)
    put(mus, 64.6, heartbeat(6, 80), 0.4)
    put(mus, 69.0, whoosh(1.0, 200, 5000, 3), 0.5)
    # ---- four against one
    put(mus, S5, drums(91.3 - S5, 140, 1.25), 0.85)
    put(mus, S5, ostinato(91.3 - S5, 140, o3), 0.26)
    put(mus, S5, pad([36.7, 73.4, 110.0, 155.6], 91.3 - S5, 900), 0.25)
    for t, r, g in ((S5, 36.7, 0.8), (76.12, 30.9, 0.9), (80.3, 36.7, 0.6), (86.88, 30.9, 0.9), (91.27, 27.5, 1.0)):
        put(mus, t, braam(3.0, r), g)
    # ---- finale
    put(mus, 91.3, pad([27.5, 41.2, 55.0, 58.3], WAVE - 91.3, 350), 0.5)
    put(mus, 93.0, heartbeat(5, 66), 0.45)
    ch = whoosh(WAVE - CH, 120, 6000, 5)
    put(mus, CH, ch * np.linspace(0.1, 1, len(ch)) ** 2, 0.8)
    put(mus, WAVE, braam(5.0, 27.5), 1.0)
    put(mus, WAVE, pad([27.5, 41.2, 55.0, 58.3, 82.4], END - WAVE, 380), 0.55)
    put(mus, 100.8, heartbeat(5, 60), 0.4)
    put(mus, END, braam(3.0, 30.9), 0.9)
    put(mus, END + 0.2, whoosh(2.2, 3000, 300, 2), 0.25)
    # ---- ambience
    put(sfx, 0.0, rain(END), 0.12)
    put(sfx, 0.0, reverb(rumble(END) * 0.3, IR_CITY, 0.5)[:int(END * SR)], 0.2)
    put(sfx, 0.0, whoosh(5.6, 150, 900, 11), 0.25)                         # wind on the fly-through
    # ---- fight sfx
    for t, size in EV['impacts']:
        put(sfx, t, punch(size), 0.9)
        if size >= 1.4:
            put(sfx, t, boom(1.5, 60 + 20 * size), 0.35 * min(size, 2.5))
    for t in EV['whoosh']:
        put(sfx, t, whoosh(0.3, 400, 3500, int(t * 100)), 0.4)
    for t in EV['land']:
        put(sfx, t, step(True, int(t * 10)), 0.55)
    for i, t in enumerate(EV['step']):
        put(sfx, t, step(False, i), 0.22)
    for i, t in enumerate(EV['bstep']):
        put(sfx, t, step(True, i), 0.6)
        put(sfx, t, boom(1.2, 42), 0.45)
    for t in EV['shatter']:
        put(sfx, t, boom(2.0, 70), 0.6)
        put(sfx, t + 0.05, rattle(1.6), 0.6)
    for t in EV['teleport']:
        put(sfx, t, zap(), 0.6)
    for t0, t1 in EV['tremor']:
        put(sfx, t0, rumble(t1 - t0) * np.minimum(1, tt(t1 - t0) / 1.0), 0.8)
    put(sfx, T4 + 0.1, rattle(1.5), 0.4)
    put(sfx, 60.4, rattle(1.4), 0.5)
    put(sfx, WAVE, boom(3.5, 35), 1.0)
    put(sfx, WAVE, whoosh(1.8, 150, 4000, 9), 0.7)
    put(sfx, WAVE + 0.1, rattle(2.0), 0.5)
    # mix
    sfx = reverb(sfx[:, 0], IR_STAIR, 0.15)[:N] * 0.5 + sfx * 0.6
    mix = mus * 0.55 + sfx
    mix[int((END + 2.7) * SR):] *= 0
    fo = int((TOTAL - 0.4) * SR)
    mix[fo:] *= np.linspace(1, 0, N - fo)[:, None]
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix = mix / np.max(np.abs(mix)) * 0.95
    os.makedirs(os.path.join(HERE, 'build'), exist_ok=True)
    wavfile.write(os.path.join(HERE, 'build', 'mix2.wav'), SR, (mix * 32767).astype(np.int16))
    print('mix', round(TOTAL, 2), 's')


if __name__ == '__main__':
    build()
