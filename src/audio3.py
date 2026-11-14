"""'Поезд в 03:17': narration (with whisper / phone / double fx), sound design and music -> build/train/mix.wav"""
import os
import numpy as np
from scipy import signal
from scipy.io import wavfile
from audio import (SR, lp, hp, bp, norm, db, tt, reverb, IR_STAIR, IR_ROOM, IR_CITY, boom, growl, hiss, heartbeat,
                   step, clang, whoosh, creak, pop, tinnitus, stinger)
from audio2 import wind, pant, drip, metal_creak, click
import timeline3 as TL
from timeline3 import S, E, W, CL, HOOK, T_DOUBLE, T_BLACK, TOTAL, ROOT
import voice3 as V

N = int((TOTAL + 0.3) * SR)
rng = np.random.default_rng(31)


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


VOX, SFX, MUS = Bus(), Bus(), Bus()


def env_keys(keys):
    ts = np.arange(N) / SR
    k = np.array(keys)
    return np.interp(ts, k[:, 0], k[:, 1])


# ---------------------------------------------------------------- generators
def tunnel_rumble(d, seed=0):
    r = np.random.default_rng(seed)
    t = tt(d)
    x = lp(r.standard_normal(len(t)), 120, 4)
    return norm(x * (0.7 + 0.3 * np.sin(2 * np.pi * 0.3 * t)))


def clatter(d, rate0, rate1, seed=0):
    """Wheel clacks (pairs) with a rate going from rate0 to rate1 (clacks/s)."""
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    t = 0.0
    k = 0
    while t < d - 0.1:
        f = t / d
        rate = rate0 + (rate1 - rate0) * f
        for off in (0.0, 0.11):
            i0 = int((t + off) * SR)
            L = int(0.09 * SR)
            if i0 + L >= len(out):
                break
            tl = np.arange(L) / SR
            hit = (bp(r.standard_normal(L), 300, 2500) * np.exp(-tl * 45) +
                   np.sin(2 * np.pi * 140 * tl) * np.exp(-tl * 35) * 0.6)
            out[i0:i0 + L] += hit
        t += 1 / max(rate, 0.3)
        k += 1
    return norm(out)


def brake_squeal(d):
    t = tt(d)
    f = 2400 + 300 * np.sin(2 * np.pi * 1.3 * t) + 120 * np.sin(2 * np.pi * 7 * t)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    e = np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.6)
    return norm(s * e + bp(noise(d), 2000, 6000) * 0.2 * e)


def air_hiss(d=1.0):
    t = tt(d)
    return norm(hp(noise(d), 2500) * np.exp(-t * 3) * np.minimum(1, t / 0.02))


def horn(d=1.8):
    t = tt(d)
    s = 0
    for f in (311.1, 370.0, 466.2):
        s = s + signal.sawtooth(2 * np.pi * f * t * (1 + 0.003 * np.sin(2 * np.pi * 5 * t)))
    s = lp(s, 2200, 2)
    e = np.minimum(1, t / 0.06) * np.minimum(1, (d - t) / 0.3)
    return norm(np.tanh(s * e * 1.5))


def hum(d, f0=100, flick=None):
    t = tt(d)
    s = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, 7))
    s = s * (0.8 + 0.2 * np.sin(2 * np.pi * 0.2 * t))
    return norm(s)


def tick():
    t = tt(0.05)
    return norm(np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 150))


def glitch_noise(d=0.4, seed=0):
    r = np.random.default_rng(seed)
    n = int(d * SR)
    x = np.zeros(n)
    i = 0
    while i < n:
        L = int(r.uniform(0.01, 0.05) * SR)
        kind = r.random()
        if kind < 0.4:
            x[i:i + L] = np.sign(np.sin(2 * np.pi * r.uniform(200, 2000) * np.arange(L) / SR))[:n - i] * 0.6
        elif kind < 0.8:
            x[i:i + L] = r.standard_normal(min(L, n - i)) * 0.5
        i += L
    return norm(x)


def static(d):
    return norm(bp(noise(d), 800, 8000) * (0.7 + 0.3 * np.sin(2 * np.pi * 3 * tt(d))))


def ringtone(d):
    out = np.zeros(int(d * SR))
    notes = [659, 784, 988, 784, 659, 0, 659, 784, 988, 1175]
    k = 0
    t0 = 0.0
    while t0 < d - 0.2:
        f = notes[k % len(notes)]
        L = int(0.16 * SR)
        tl = np.arange(L) / SR
        if f:
            n = (np.sign(np.sin(2 * np.pi * f * tl)) * 0.4 + np.sin(2 * np.pi * f * tl)) * np.exp(-tl * 8)
            i0 = int(t0 * SR)
            out[i0:i0 + L] += n[:max(0, min(L, len(out) - i0))]
        t0 += 0.18
        k += 1
        if k % len(notes) == 0:
            t0 += 0.6
    return norm(lp(out, 5000))


def vibrate(d):
    t = tt(d)
    gate = ((t % 1.0) < 0.6).astype(float)
    return norm(np.sin(2 * np.pi * 150 * t) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 30 * t))) * gate)


def beeps(n=3, f=425):
    out = np.zeros(int(n * 0.6 * SR))
    for k in range(n):
        i0 = int(k * 0.6 * SR)
        L = int(0.3 * SR)
        out[i0:i0 + L] += np.sin(2 * np.pi * f * np.arange(L) / SR)
    return norm(out)


def ping():
    out = np.zeros(int(0.6 * SR))
    for k, f in enumerate((1320, 1760)):
        i0 = int(k * 0.12 * SR)
        L = int(0.45 * SR)
        tl = np.arange(L) / SR
        out[i0:i0 + L] += np.sin(2 * np.pi * f * tl) * np.exp(-tl * 9)
    return norm(out)


def crowd_breath(d, seed=0):
    r = np.random.default_rng(seed)
    out = np.zeros(int(d * SR))
    for k in range(20):
        L = int(r.uniform(0.4, 1.0) * SR)
        i0 = int(r.uniform(0, d - 1.0) * SR)
        e = np.sin(np.pi * np.arange(L) / L) ** 2
        out[i0:i0 + L] += bp(r.standard_normal(L), r.uniform(300, 600), r.uniform(1500, 3000)) * e
    return norm(out)


# ---------------------------------------------------------------- voice
def build_voice():
    parts = {}
    for cid, part, i0, i1, gap, fx in TL.CLIPS:
        if part not in parts:
            parts[part] = V.load_part(part)
        a, b = CL[cid]['src']
        x = V.fade_edges(parts[part][int(a * SR):int(b * SR)])
        t0 = CL[cid]['t0']
        if fx == 'whisper':
            VOX.add(t0, V.whisper_fx(x) * 1.1)
        elif fx == 'phone':
            VOX.add(t0, V.phone_fx(x) * 0.95)
        else:
            VOX.add(t0, x)
    VOX.add(T_DOUBLE, V.double_line() * 0.95)


# ---------------------------------------------------------------- sound design
def build_sfx():
    X = SFX
    # hook: the train rushes out of the tunnel
    X.add(0, tunnel_rumble(HOOK + 0.5, 1) * np.linspace(0.3, 1, int((HOOK + 0.5) * SR)), db(-8))
    X.add(0.6, clatter(HOOK - 0.6, 3, 9, 1) * np.linspace(0.2, 1, int((HOOK - 0.6) * SR)), db(-12))
    X.add(2.9, reverb(horn(1.6), IR_STAIR, 0.4), db(-9))
    X.add(HOOK - 0.3, boom(1.5, 80), db(-8))
    X.add(0.0, glitch_noise(0.5, 2), db(-20))
    # legend
    X.add(S('A1') + 1.2, glitch_noise(0.35, 3), db(-20))
    X.add(S('A2') - 0.1, static(E('A2') - S('A2') + 0.4), db(-26))
    X.add(S('A3'), wind(E('A4') - S('A3'), 4), db(-30))
    X.add(W('A4', 'решаешь') + 0.9, bp(noise(0.2), 200, 2000) * np.exp(-tt(0.2) * 20), db(-18))  # laptop shut
    # the descent and the station
    for i, h in enumerate(np.arange(S('B1') - 0.1, S('B2'), 0.55)):
        X.add(h, reverb(step(False, 10 + i) * 0.5, IR_STAIR, 0.5), db(-20))
    t_stop = W('B5', 'останавливаются')
    X.add(S('B2') - 0.2, hum(t_stop - S('B2') + 0.2, 100), db(-34))
    for k in range(6):
        X.add(S('B2') + 0.5 + k * 1.3, bp(noise(0.08), 2000, 7000) * np.exp(-tt(0.08) * 40), db(-28))  # lamp clicks
    for i, h in enumerate((S('B2') + 1.5, S('B3') + 2.0, S('B3') + 5.0, S('B4') + 1.0)):
        X.add(h, reverb(drip(), IR_STAIR, 0.6), db(-24))
    for k in np.arange(W('B3', '03:16'), t_stop, 1.0):
        X.add(k, tick(), db(-22))
    X.add(t_stop, glitch_noise(0.3, 5), db(-16))
    X.add(t_stop + 0.25, tinnitus(3.0), db(-38))           # absolute silence
    # light in the tunnel, the train arrives
    tl = S('B7')
    X.add(tl - 0.3, tunnel_rumble(E('B8') - tl + 2, 2) * np.linspace(0.05, 1, int((E('B8') - tl + 2) * SR)), db(-9))
    X.add(tl + 1.0, reverb(wind(2.5, 6), IR_STAIR, 0.3), db(-22))
    ta = S('B8') - 0.2
    stop_t = W('B8', 'перед') - 0.1
    X.add(ta, clatter(stop_t - ta, 8, 1.5, 2), db(-10))
    X.add(stop_t - 1.6, brake_squeal(1.8), db(-18))
    X.add(stop_t + 0.1, air_hiss(1.2), db(-16))
    X.add(S('B9') + 0.05, air_hiss(0.8), db(-14))
    X.add(S('B9') + 0.1, whoosh(0.6, 300, 1200, 4), db(-20))
    X.add(S('B9') + 1.3, bp(noise(0.15), 100, 900) * np.exp(-tt(0.15) * 20), db(-16))     # doors bump open
    # inside the carriage
    X.add(S('C1') - 0.2, hum(S('D4') - S('C1'), 120), db(-38))
    X.add(W('C4', 'поднимает'), metal_creak(0.6, 260, 6) * 0.5, db(-28))
    X.add(S('C5'), heartbeat(14, 64), db(-14))
    X.add(WT_ := W('C9', '03:17'), stinger(2.0) * 0.6, db(-18))
    # chase
    tt_ = W('D1', 'поворачивают') - 0.15
    X.add(tt_, stinger(2.5), db(-8))
    X.add(tt_, glitch_noise(0.25, 7), db(-14))
    X.add(tt_ + 0.1, crowd_breath(3.0, 2), db(-20))
    X.add(W('D3', 'встаёт') - 0.1, step(True, 3), db(-12))
    t_run = S('D4') - 0.05
    for i, h in enumerate(np.arange(t_run, S('D6') + 0.2, 0.19)):
        X.add(h, reverb(step(False, 40 + i), IR_STAIR, 0.4), db(-14), pan=0.2 * (-1) ** i)
    X.add(t_run, pant(E('D6') - t_run + 3.5, 2.6, 3), db(-20))
    X.add(S('D5'), beeps(3, 880) * 0.6, db(-22))                                         # door warning
    X.add(W('D5', 'высовываются') - 0.2, crowd_breath(2.5, 3), db(-14))
    X.add(W('D5', 'высовываются') - 0.2, glitch_noise(0.3, 8), db(-16))
    X.add(W('D5', 'рук'), bp(noise(0.3), 80, 800) * np.exp(-tt(0.3) * 10), db(-10))    # doors slam
    for i, h in enumerate(np.arange(S('D6'), E('D6') + 0.1, 0.2)):
        X.add(h, reverb(step(False, 80 + i), IR_STAIR, 0.5), db(-14))
    th = WT_h = W('D7', 'сигнал') - 0.4
    X.add(th, reverb(horn(2.2), IR_STAIR, 0.5), db(-10))
    X.add(th, tunnel_rumble(3, 4), db(-10))
    tv = W('D8', 'исчезает')
    X.add(tv - 0.3, whoosh(1.6, 3000, 200, 5)[::-1].copy(), db(-12))
    X.add(tv + 0.2, glitch_noise(0.6, 9), db(-18))
    # street, the call
    X.add(S('E1') - 0.2, wind(S('G1') - S('E1') + 8, 7), db(-26))
    X.add(S('E3') + 0.2, vibrate(E('E3') - S('E3') + 2.0), db(-24))
    X.add(S('E3') + 0.2, ringtone(E('E3') - S('E3') + 2.0), db(-20))
    X.add(S('E4') + 0.3, click(), db(-16))
    X.add(S('F1') + 0.1, beeps(3, 425), db(-20))
    X.add(S('F2') + 0.2, ping(), db(-16))
    X.add(WT_f := W('F4', 'секунд'), stinger(2.5) * 0.7, db(-14))
    # the impossible ending
    X.add(S('G5') - 0.15, glitch_noise(0.4, 11), db(-16))
    X.add(S('G5') - 0.1, hum(3.0, 60) * np.exp(-tt(3.0) * 0.5), db(-22))
    X.add(S('G5'), stinger(2.5) * 0.7, db(-14))
    X.add(W('G6', '03:17'), tick(), db(-16))
    th1 = S('H1') - 0.1
    X.add(th1, lp(tunnel_rumble(6, 9), 200), db(-6))
    X.add(th1 + 0.5, lp(clatter(5.0, 2, 7, 6), 900), db(-14))
    X.add(W('H3', 'появились') - 0.2, glitch_noise(0.8, 12), db(-16))
    X.add(W('H4', '03:17'), tick(), db(-12))
    X.add(S('H5'), whoosh(2.0, 200, 3000, 13), db(-18))
    # inside the train again: steady clatter until the very end, then a hard cut
    t_in = S('H6') - 0.1
    X.add(t_in, clatter(T_BLACK - t_in, 3.2, 3.2, 14), db(-16))
    X.add(t_in, tunnel_rumble(T_BLACK - t_in, 15), db(-14))
    X.add(T_BLACK + 1.0, boom(2.5, 50) * 0.5, db(-16))


# ---------------------------------------------------------------- music
def tone(f, d, kind='sine'):
    t = tt(d)
    if kind == 'saw':
        return signal.sawtooth(2 * np.pi * f * t)
    return np.sin(2 * np.pi * f * t)


def pad(freqs, d, cutoff=800):
    s = 0
    for f in freqs:
        for det in (-0.004, 0.0, 0.004):
            s = s + tone(f * (1 + det), d, 'saw')
    return norm(lp(s, cutoff))


def music_box(d, start, notes, period=0.5):
    out = np.zeros(int(d * SR))
    for k, n in enumerate(notes):
        if n is None:
            continue
        f = 440 * 2 ** ((n - 69) / 12)
        i0 = int((start + k * period) * SR)
        L = int(1.2 * SR)
        tl = np.arange(L) / SR
        p = (np.sin(2 * np.pi * f * tl) + 0.3 * np.sin(2 * np.pi * 2 * f * tl) + 0.15 * np.sin(2 * np.pi * 3.01 * f * tl))
        p *= np.exp(-tl * 4)
        if i0 + L < len(out):
            out[i0:i0 + L] += p
    return out


def build_music():
    d = TOTAL + 0.3
    n = int(d * SR)
    t = tt(d)
    # D minor tension bed + a darker cluster
    bed = pad([73.42, 110.0, 146.83, 174.61], d, 600)
    cluster = pad([146.83, 155.56, 220.0, 233.08], d, 900)
    # pulse (8ths), tempo up in the chase
    pulse = np.zeros(n)
    tt0 = 0.0
    while tt0 < d:
        chase = S('D1') - 0.2 <= tt0 <= E('D8')
        per = 0.214 if chase else 0.5
        L = int(0.2 * SR)
        tl = np.arange(L) / SR
        nt = signal.sawtooth(2 * np.pi * 73.42 * tl) * np.exp(-tl * 14)
        i0 = int(tt0 * SR)
        pulse[i0:i0 + L] += nt[:max(0, min(L, n - i0))]
        tt0 += per
    pulse = lp(pulse, 500, 3)
    hits = np.zeros(n)
    for h in np.arange(S('D1') - 0.2, E('D8'), 0.856):
        L = int(0.5 * SR)
        tl = np.arange(L) / SR
        hh = np.sin(2 * np.pi * np.cumsum(np.linspace(90, 40, L)) / SR) * np.exp(-tl * 7)
        i0 = int(h * SR)
        hits[i0:i0 + L] += hh[:max(0, min(L, n - i0))]
    # mystical music-box motif (opening / photo / ending)
    motif = [74, 77, 81, 80, 74, None, 77, 76, 72, None, 74, None]
    mb = music_box(d, 0.3, motif, 0.42) + music_box(d, S('A3'), motif, 0.5) + music_box(d, S('F3'), motif, 0.5) + \
        music_box(d, S('H5') - 0.5, motif[:8], 0.55)
    t_cut = E('H6') + 0.25                 # sharp silence before the last line
    E_bed = env_keys([(0, 0.5), (HOOK, 0.7), (S('C4'), 0.7), (S('C5'), 0.25), (S('D1') - 0.3, 0.25),
                      (S('D1'), 0.9), (E('D8'), 0.9), (S('E1'), 0.5), (S('G5'), 0.8), (t_cut - 0.02, 0.9),
                      (t_cut, 0.0), (d, 0.0)])
    E_cluster = env_keys([(0, 0.0), (S('B5'), 0.0), (S('B7'), 0.5), (S('C4'), 0.4), (S('C5'), 0.15),
                          (S('D1'), 0.8), (E('D8'), 0.6), (S('E1'), 0.2), (S('E5'), 0.5), (S('G5'), 0.8),
                          (t_cut - 0.02, 1.0), (t_cut, 0.0), (d, 0.0)])
    E_pulse = env_keys([(0, 0.0), (S('B2'), 0.0), (S('B3'), 0.35), (W('B5', 'останавливаются'), 0.35),
                        (W('B5', 'останавливаются') + 0.01, 0.0), (S('C1'), 0.0), (S('C2'), 0.3), (S('C4'), 0.3),
                        (S('C5'), 0.0), (S('D1') - 0.2, 0.0), (S('D1'), 1.0), (E('D8'), 1.0), (E('D8') + 0.5, 0.0),
                        (S('H1'), 0.0), (S('H1') + 2, 0.6), (t_cut - 0.02, 0.8), (t_cut, 0.0), (d, 0.0)])
    E_hits = env_keys([(0, 0.0), (S('D1') - 0.2, 0.0), (S('D1'), 1.0), (E('D8'), 1.0), (E('D8') + 0.2, 0.0),
                       (d, 0.0)])
    # absolute silence when the clock stops (no music at all) until the light appears
    sil0, sil1 = W('B5', 'останавливаются'), S('B7')
    quiet = env_keys([(0, 1), (sil0, 1), (sil0 + 0.05, 0.0), (sil1, 0.0), (sil1 + 1.5, 1), (d, 1)])
    L = (bed * 0.35 * E_bed + cluster * 0.2 * E_cluster + pulse * 0.6 * E_pulse + norm(hits) * 0.6 * E_hits)
    L = L * quiet + mb * 0.18 * (t < t_cut)
    L[int(t_cut * SR):] = 0
    MUS.add(0, np.stack([L, L], 1))
    MUS.add(0, reverb(L * 0.35, IR_CITY, 0.6)[:n], 0.4)
    MUS.x[int(t_cut * SR):] = 0


def main():
    build_voice()
    build_sfx()
    build_music()
    Vx = VOX.x
    env = np.abs(Vx).max(1)
    win = int(0.08 * SR)
    env = np.convolve(env, np.ones(win) / win, 'same')
    env = np.clip(env / (np.percentile(env[env > 0.01], 90) + 1e-6), 0, 1)
    Sx = SFX.x * (1 - 0.55 * env)[:, None] * db(-6)
    Mx = MUS.x * (1 - 0.35 * env)[:, None] * db(-15)
    Sx = np.tanh(Sx * 1.2) / 1.2
    mix = Vx + Sx + Mx
    cut = int(T_BLACK * SR)          # hard cut on the blackout (only the late low boom remains)
    mix[cut:int((T_BLACK + 1.0) * SR)] *= 0
    fo = int((TOTAL - 0.8) * SR)
    mix[fo:] *= np.linspace(1, 0, N - fo)[:, None]
    mix = mix / max(1.0, np.max(np.abs(mix)) / 0.98)
    out = os.path.join(ROOT, 'build', 'train')
    os.makedirs(out, exist_ok=True)
    wavfile.write(os.path.join(out, 'mix.wav'), SR, (mix * 32767).astype(np.int16))
    for name, x in (('voice', Vx), ('sfx', Sx), ('music', Mx)):
        wavfile.write(os.path.join(out, f'{name}.wav'), SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))
    print('mix written', N / SR)


if __name__ == '__main__':
    main()
