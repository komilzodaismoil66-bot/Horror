"""Episode 2: procedural music + sound design + voice mix -> build/ep2/mix.wav"""
import os
import numpy as np
from scipy import signal
from scipy.io import wavfile
from audio import (SR, lp, hp, bp, norm, db, tt, reverb, IR_STAIR, IR_ROOM, IR_CITY, boom, crackle, growl,
                   hiss, roar, heartbeat, step, clang, whoosh, creak, pop, tinnitus, stinger, siren)
import timeline2 as TL
from timeline2 import T, OFF, DUR, TOTAL, ROOT
import scenes2 as SC

N = int((TOTAL + 0.3) * SR)
rng = np.random.default_rng(22)


def noise(d):
    return rng.standard_normal(int(d * SR))


class Bus:
    def __init__(self):
        self.x = np.zeros((N, 2))

    def add(self, t0, s, gain=1.0, pan=0.0):
        if s.ndim == 1:
            s = np.stack([s * np.sqrt(1 - pan), s * np.sqrt(1 + pan)], 1)
        i0 = int(t0 * SR)
        if i0 < 0:
            s, i0 = s[-i0:], 0
        i1 = min(N, i0 + len(s))
        if i1 > i0:
            self.x[i0:i1] += s[:i1 - i0] * gain


SFX = Bus()
MUS = Bus()


def env_keys(keys):
    """Piecewise-linear envelope over the whole timeline: keys = [(t, value), ...]."""
    ts = np.arange(N) / SR
    k = np.array(keys)
    return np.interp(ts, k[:, 0], k[:, 1])


# ---------------------------------------------------------------- extra generators
def wind(d, seed=0):
    r = np.random.default_rng(seed)
    t = tt(d)
    x = r.standard_normal(len(t))
    low = lp(x, 350) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + 1))
    howl = np.zeros_like(x)
    seg = 4096
    for i in range(0, len(x), seg):
        f = 600 + 350 * np.sin(2 * np.pi * 0.07 * i / SR) + 150 * np.sin(2 * np.pi * 0.23 * i / SR)
        chunk = x[max(0, i - 2048):i + seg]
        howl[i:i + seg] = bp(chunk, f * 0.85, f * 1.15)[-len(x[i:i + seg]):]
    return norm(norm(low) * 0.7 + norm(howl) * 0.5 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t)))


def pant(d, rate=2.2, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    period = 1 / rate
    k = 0
    while k * period < d - 0.3:
        L = int(0.24 * SR)
        e = np.sin(np.pi * np.arange(L) / L) ** 2
        b = bp(r.standard_normal(L), 400 if k % 2 else 700, 2600) * e * (0.7 if k % 2 else 1.0)
        i0 = int(k * period * SR)
        out[i0:i0 + L] += b[:len(out) - i0]
        k += 1
    return norm(out)


def drip():
    t = tt(0.25)
    f = np.linspace(1400, 2100, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)


def metal_creak(d=1.6, f0=95, seed=0):
    t = tt(d)
    f = f0 * (1 + 0.25 * np.sin(2 * np.pi * 0.6 * t) + 0.1 * np.sin(2 * np.pi * 3.1 * t))
    s = signal.sawtooth(2 * np.pi * np.cumsum(f) / SR)
    s = bp(s, 300, 3000) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 7 * t)))
    return norm(s * np.sin(np.pi * np.minimum(1, t / d)))


def crunch(d=0.5, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    for i in range(int(d * 40)):
        i0 = r.integers(0, len(out) - 800)
        L = r.integers(200, 800)
        out[i0:i0 + L] += bp(r.standard_normal(L), 600, 5000) * np.exp(-np.arange(L) / (L / 4)) * r.uniform(0.3, 1)
    return norm(out)


def sigh(d=1.6):
    t = tt(d)
    e = np.minimum(1, t / 0.15) * np.exp(-np.maximum(0, t - 0.15) * 1.8)
    return norm(bp(noise(d), 250, 1800) * e)


def click():
    t = tt(0.04)
    return norm(hp(noise(0.04), 2000) * np.exp(-t * 200) + np.sin(2 * np.pi * 3000 * t) * np.exp(-t * 150) * 0.5)


# ---------------------------------------------------------------- music
NOTE = {'D2': 73.42, 'Eb2': 77.78, 'A2': 110.0, 'D3': 146.83, 'F3': 174.61, 'A3': 220.0, 'C4': 261.63,
        'D4': 293.66, 'Eb4': 311.13, 'F4': 349.23, 'A4': 440.0, 'Bb3': 233.08}
BEAT = 0.6


def saw_pad(freqs, d, cutoff=900, det=0.004):
    t = tt(d)
    s = 0
    for f in freqs:
        for dt_ in (-det, 0, det):
            s = s + signal.sawtooth(2 * np.pi * f * (1 + dt_) * t + rng.uniform(0, 6))
    return norm(lp(s, cutoff, 2))


def build_music():
    d = TOTAL + 0.3
    t = tt(d)
    n = len(t)
    t_slam = T(7, 'дверь') + 0.05
    # --- tension pad (cluster), calm pad (minor chord), mystery pad
    tension = saw_pad([NOTE['D3'], NOTE['Eb4'], NOTE['A3']], d, 700)
    calm = saw_pad([NOTE['D3'], NOTE['F3'], NOTE['A3'], NOTE['C4']], d, 600, 0.003)
    mystery = saw_pad([NOTE['D3'], NOTE['A3'], NOTE['Bb3']], d, 500, 0.006)
    # --- bass ostinato (8ths), alternating D / Eb every bar
    bass = np.zeros(n)
    for k in range(int(d / (BEAT / 2))):
        t0 = k * BEAT / 2
        f = NOTE['D2'] if (k // 8) % 2 == 0 else NOTE['Eb2']
        L = int(0.26 * SR)
        tl = np.arange(L) / SR
        note = signal.sawtooth(2 * np.pi * f * tl) * np.exp(-tl * 9) * (1.0 if k % 2 == 0 else 0.7)
        i0 = int(t0 * SR)
        bass[i0:i0 + L] += note[:max(0, min(L, n - i0))]
    bass = lp(bass, 420, 3)
    # --- drums: low tom on beats, accent every bar, snare-ish hit on 3
    drums = np.zeros(n)
    for k in range(int(d / BEAT)):
        i0 = int(k * BEAT * SR)
        L = int(0.5 * SR)
        tl = np.arange(L) / SR
        f = np.linspace(95, 45, L)
        hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tl * 7) + lp(rng.standard_normal(L), 300) * np.exp(
            -tl * 18) * 0.4
        g = 1.0 if k % 4 == 0 else 0.6
        if k % 4 == 2:
            hit = hit + bp(rng.standard_normal(L), 900, 5000) * np.exp(-tl * 22) * 0.35
        drums[i0:i0 + L] += hit[:max(0, min(L, n - i0))] * g
    # --- string tremolo (high dissonance)
    trem = (signal.sawtooth(2 * np.pi * NOTE['D4'] * 2 * t) + signal.sawtooth(2 * np.pi * NOTE['Eb4'] * 2 * t))
    trem = bp(trem, 900, 4000) * (0.55 + 0.45 * np.sin(2 * np.pi * 11 * t))
    # --- envelopes per section
    E_chase = env_keys([(0, 1.0), (OFF[3] - 0.5, 1.0), (OFF[3] + 0.3, 0.0), (OFF[6], 0.0), (OFF[6] + 1.5, 0.35),
                        (t_slam - 0.1, 0.55), (t_slam + 0.05, 0.0), (d, 0.0)])
    E_tension = env_keys([(0, 0.6), (OFF[3], 0.7), (OFF[4], 0.9), (OFF[5] + 2, 0.6), (OFF[6], 0.5),
                          (t_slam - 0.1, 0.7), (t_slam + 0.05, 0.0), (d, 0.0)])
    E_pulse = env_keys([(0, 1.0), (OFF[3], 1.0), (OFF[3] + 0.4, 0.45), (OFF[6], 0.45), (t_slam - 0.1, 0.8),
                        (t_slam + 0.05, 0.0), (d, 0.0)])
    E_calm = env_keys([(0, 0), (t_slam + 0.8, 0.0), (t_slam + 3.0, 0.5), (OFF[10] - 0.5, 0.6), (OFF[10] + 1, 0.0),
                       (d, 0.0)])
    E_myst = env_keys([(0, 0), (OFF[10] - 0.8, 0.0), (OFF[10] + 1.0, 0.55), (TOTAL - 1.5, 0.6), (TOTAL, 0.0),
                       (d, 0.0)])
    L = (tension * 0.35 * E_tension + bass * 0.9 * E_pulse + norm(drums) * 0.8 * E_chase +
         norm(trem) * 0.18 * E_chase + calm * 0.55 * E_calm + mystery * 0.55 * E_myst)
    MUS.add(0, np.stack([L, L], 1), 1.0)
    MUS.add(0, reverb(L * 0.4, IR_CITY, 0.6)[:n], 0.5)


# ---------------------------------------------------------------- sfx arrangement
def build_sfx():
    E = SFX
    # 1. escape (same beats as the end of episode 1)
    tesc = T(1, 'выскакиваешь') - 0.35
    E.add(tesc - 0.05, boom(1.2, 110) * 0.8, db(-9))
    E.add(tesc + 0.3, whoosh(0.4, 600, 3000, 8), db(-12))
    E.add(tesc + 0.45, reverb(boom(1.0, 90), IR_CITY, 0.3), db(-12))
    E.add(tesc + 0.5, reverb(roar(1.5), IR_CITY, 0.5), db(-12))
    E.add(0, crackle(OFF[3], 28, 5), db(-17))
    E.add(0.2, reverb(siren(10) * 0.6, IR_CITY, 0.6), db(-28), pan=0.5)
    # 2. heavy monster steps behind + running
    for h in SC.mon_impacts(OFF[2] - 0.05, T(2, 'ты') - 0.1, SC.STEP_SPEED, SC.STEP_SEED):
        E.add(h, reverb(step(True, int(h * 10)), IR_CITY, 0.45), db(-4))
        E.add(h, boom(0.8, 60) * 0.5, db(-12))
    E.add(OFF[2] + 0.3, reverb(growl(2.0, 42, 24, 450, 3), IR_CITY, 0.4), db(-16))
    t_run0 = T(2, 'ты') - 0.1
    tj = T(2, 'перепрыгиваешь') + 0.05
    t_quiet = T(2, 'стараешься') - 0.15
    k = 0
    tt_ = tesc + 0.1
    while tt_ < t_quiet + 0.4:
        if not (tj < tt_ < tj + 0.62):
            E.add(tt_, step(False, 100 + k), db(-15 - (6 if tt_ > t_quiet else 0)), pan=0.15 * (-1) ** k)
        tt_ += 0.21
        k += 1
    E.add(t_run0, pant(t_quiet - t_run0 + 0.8, 2.4, 1), db(-22))
    E.add(tj - 0.05, whoosh(0.6, 400, 2500, 3), db(-14))
    E.add(tj + 0.62, step(True, 9) * 0.7, db(-10))
    E.add(tj + 0.64, crunch(0.5, 2), db(-14))
    for i, h in enumerate(np.arange(t_run0 + 0.5, t_quiet + 1.5, 1.05)):
        E.add(h, reverb(step(True, 200 + i), IR_CITY, 0.6), db(-14 - i * 1.5))
    # quiet: careful steps, cold wind from here on
    E.add(t_quiet, wind(OFF[7] - t_quiet + 2, 1), db(-20))
    for i, h in enumerate(np.arange(t_quiet + 0.6, OFF[3] + 2.2, 0.55)):
        E.add(h, step(False, 300 + i) * 0.5, db(-24))
    # 3. hide
    t_dash = T(3, 'быстро')
    for i in range(3):
        E.add(t_dash + i * 0.18, step(False, 400 + i), db(-17))
    E.add(t_dash + 0.6, bp(noise(0.4), 500, 3000) * np.exp(-tt(0.4) * 8), db(-20))
    E.add(T(3, 'замираешь'), heartbeat(30, 98), db(-14))
    # 4. the monster passes the car
    t0p = OFF[4] - 0.6
    imp = SC.mon_impacts(OFF[4] - 0.3, T(5, 'удаляются', end=True) + 0.5, SC.PASS_SPEED, SC.PASS_SEED)
    for i, h in enumerate(imp):
        fadeg = 0 if h < OFF[5] else -(h - OFF[5]) * 7
        E.add(h, reverb(step(True, 500 + i), IR_CITY, 0.4), db(-6 + fadeg))
        E.add(h, boom(0.7, 55) * 0.4, db(-14 + fadeg))
    for i, h in enumerate(np.arange(OFF[5] + 0.6, OFF[5] + 3.2, 1.25)):
        E.add(h, reverb(step(True, 600 + i), IR_CITY, 0.7), db(-14 - i * 4))
    E.add(OFF[4] + 0.6, growl(2.2, 40, 18, 350, 9), db(-17))
    E.add(OFF[4] + 1.6, bp(noise(0.8), 1500, 6000) * np.sin(np.pi * tt(0.8) / 0.8), db(-26))   # sniff
    t_h = T(4, 'его')
    for i in range(7):
        E.add(t_h + 0.3 + i * 0.33 + rng.uniform(0, 0.1), click() * 0.5, db(-20), pan=0.3)
    E.add(T(4, 'касаются'), metal_creak(1.4, 120, 1), db(-20))
    E.add(T(4, 'ты'), tinnitus(2.0), db(-36))
    # 5. peek, go on
    E.add(T(5, 'выглядываешь'), bp(noise(0.5), 400, 2500) * np.exp(-tt(0.5) * 5), db(-24))
    for i, h in enumerate(np.arange(T(5, 'продолжаешь'), OFF[6] + 0.3, 0.55)):
        E.add(h, step(False, 700 + i) * 0.5, db(-24))
    # 6. outskirts / rubble
    E.add(OFF[6] - 0.1, wind(OFF[7] - OFF[6] + 1, 3), db(-15))
    E.add(OFF[6], reverb(boom(3, 40) * 0.5, IR_CITY, 0.6), db(-24))
    E.add(T(6, 'завален'), crunch(0.8, 4) * 0.6, db(-24))
    # 7. squeeze + heavy door
    E.add(OFF[7], crunch(1.6, 5), db(-15))
    E.add(OFF[7] + 0.9, metal_creak(0.9, 80, 2), db(-20))
    t_slam = T(7, 'дверь') + 0.05
    E.add(t_slam - 1.7, reverb(metal_creak(1.7, 70, 3), IR_STAIR, 0.4), db(-12))
    E.add(t_slam, reverb(boom(2.5, 70), IR_STAIR, 0.55), db(-3))
    E.add(t_slam + 0.05, reverb(clang(1.5) * 0.5, IR_STAIR, 0.5), db(-14))
    E.add(t_slam + 0.4, reverb(metal_creak(0.6, 160, 4), IR_ROOM, 0.4), db(-22))    # wheel latch
    E.add(t_slam + 0.3, bp(noise(1.5), 2000, 8000) * np.exp(-tt(1.5) * 2) * 0.4, db(-24))   # dust trickle
    # 8. inside: quiet, drips, flashlight, lantern, sigh
    t_on = T(8, 'темно') + 0.15
    E.add(t_on, click(), db(-12))
    for i, h in enumerate((OFF[8] + 0.9, OFF[8] + 2.6, OFF[8] + 4.3, OFF[9] + 0.4, OFF[10] + 1.5, OFF[11] + 2.0,
                           OFF[12] + 1.2)):
        E.add(h, reverb(drip(), IR_ROOM, 0.5), db(-24))
    E.add(T(8, 'впервые') - 0.1, whoosh(0.5, 300, 1200, 9), db(-22))
    E.add(T(8, 'чувствуешь') - 0.3, bp(noise(0.8), 300, 2000) * np.sin(np.pi * tt(0.8) / 0.8), db(-26))
    E.add(T(8, 'безопасности'), sigh(1.8), db(-17))
    # poll: soft pops for each card, and the creature above starts listening
    for tt_ in (OFF[10], OFF[11], OFF[12], OFF[13]):
        E.add(tt_ - 0.1, pop(), db(-18))
        E.add(tt_ - 0.12, whoosh(0.3, 800, 3000, 10), db(-24))
    for i, h in enumerate(SC.mon_impacts(OFF[10] - 0.2, OFF[13] - 0.5, 0.2, 7)):
        E.add(h, lp(step(True, 800 + i), 300), db(-20))          # muffled steps on the surface above
    E.add(OFF[13] + 0.8, lp(growl(2.5, 36, 18, 300, 11), 400), db(-16))
    E.add(TOTAL - 1.6, stinger(1.6) * np.linspace(1, 0, int(1.6 * SR)), db(-14))


def load_voice():
    V = np.zeros((N, 2))
    for i in range(1, TL.NPARTS + 1):
        sr, a = wavfile.read(os.path.join(ROOT, 'audio', 'ep2', 'fast', f'part{i}.wav'))
        a = a.astype(np.float64) / 32768
        if a.ndim == 1:
            a = np.stack([a, a], 1)
        i0 = int(OFF[i] * SR)
        V[i0:i0 + len(a)] += a[:N - i0]
    return V


def main():
    build_music()
    build_sfx()
    V = load_voice()
    env = np.abs(V).max(1)
    win = int(0.08 * SR)
    env = np.convolve(env, np.ones(win) / win, 'same')
    env = np.clip(env / (np.percentile(env[env > 0.01], 90) + 1e-6), 0, 1)
    duck = (1 - 0.6 * env)[:, None]
    S = SFX.x * duck * db(-6)
    M = MUS.x * (1 - 0.35 * env)[:, None] * db(-17)
    S = np.tanh(S * 1.2) / 1.2
    mix = V + S * 0.9 + M
    fo = int((TOTAL - 0.8) * SR)
    mix[fo:] *= np.linspace(1, 0, N - fo)[:, None]
    mix = mix / max(1.0, np.max(np.abs(mix)) / 0.98)
    out = os.path.join(ROOT, 'build', 'ep2')
    os.makedirs(out, exist_ok=True)
    wavfile.write(os.path.join(out, 'mix.wav'), SR, (mix * 32767).astype(np.int16))
    for name, x in (('voice', V), ('sfx', S), ('music', M)):
        wavfile.write(os.path.join(out, f'{name}.wav'), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    print('mix written', N / SR)


if __name__ == '__main__':
    main()
