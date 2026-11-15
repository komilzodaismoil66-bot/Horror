"""Original drift-phonk beat for the Patrick Jane edit + its beat grid (build/phonk/phonk.wav, beats.json).

130 BPM, F# minor. 16 bars ≈ 29.5 s:
  bars 1-4   intro: filtered cowbell melody, vinyl crackle, riser in bar 4
  bars 5-12  DROP: 808 kick + distorted 808 bass + clap + hats + cowbell lead
  bars 13-14 break: bass and kick out, cowbell + reverse swell
  bars 15-16 final drop, tape-stop on the last beat
"""
import json
import os
import numpy as np
from scipy import signal
from scipy.io import wavfile
from audio import SR, lp, hp, bp, norm, reverb, IR_ROOM, IR_CITY

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'build', 'phonk')
BPM = 130
B = 60 / BPM                  # one beat
BARS = 16
TOTAL = BARS * 4 * B + 1.2
N = int(TOTAL * SR)
rng = np.random.default_rng(130)


def tt(d):
    return np.arange(int(d * SR)) / SR


def place(bus, t0, s, g=1.0):
    i0 = int(t0 * SR)
    i1 = min(len(bus), i0 + len(s))
    if i1 > i0:
        bus[i0:i1] += s[:i1 - i0] * g


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def kick():
    t = tt(0.55)
    f = 45 + 120 * np.exp(-t * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    s += hp(rng.standard_normal(len(t)), 2000) * np.exp(-t * 120) * 0.25
    return np.tanh(s * 2.2)


def clap():
    t = tt(0.35)
    n = bp(rng.standard_normal(len(t)), 900, 6000)
    env = np.exp(-t * 18)
    for d in (0.0, 0.011, 0.022):
        i = int(d * SR)
        env[i:i + 200] += 0.8
    return norm(n * env + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.3)


def hat(open_=False):
    d = 0.28 if open_ else 0.05
    t = tt(d)
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * (9 if open_ else 70))


def cowbell(note, d=0.3):
    """TR-808 style cowbell (two detuned square tones through a band-pass), pitched to `note`."""
    t = tt(d)
    k = midi(note) / midi(73)
    s = signal.square(2 * np.pi * 540 * k * t) + signal.square(2 * np.pi * 800 * k * t)
    s = bp(s, 600 * k, min(3200 * k, 15000))
    return s * (np.exp(-t * 18) * 0.7 + np.exp(-t * 5) * 0.3)


def bass808(note, d):
    t = tt(d)
    f = midi(note) * (1 + 0.6 * np.exp(-t * 30))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3)
    s = np.tanh(s * 3.0) * 0.8 + np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4
    return s * np.minimum(1, t / 0.005)


def crackle(d):
    x = np.zeros(int(d * SR))
    idx = rng.integers(0, len(x), int(d * 40))
    x[idx] = rng.uniform(-1, 1, len(idx))
    return lp(x, 6000) * 0.5 + lp(rng.standard_normal(len(x)), 300) * 0.02


def riser(d):
    t = tt(d)
    x = rng.standard_normal(len(t))
    out = np.zeros_like(x)
    seg = 1024
    for i in range(0, len(x), seg):
        f = 300 + 7000 * (i / len(x)) ** 2
        out[i:i + seg] = bp(x[max(0, i - 2048):i + seg], f * 0.7, min(f * 1.4, 20000))[-len(x[i:i + seg]):]
    return norm(out) * (t / d) ** 1.5


# melody (16th-note grid over one bar), F# minor: F#=66/78, A=69/81, B=71, C#=73, E=76
LEAD = [78, None, 78, 81, None, 78, 76, None, 73, None, 73, 76, None, 73, 71, 73]
LEAD_B = [78, None, 81, 83, None, 81, 78, None, 85, None, 83, 81, None, 78, 76, 78]
BASS = [(42, 0, 1.5), (42, 1.75, 0.75), (45, 2.5, 1.0), (40, 3.5, 0.5)]   # (note, beat, length in beats)


def build():
    drums = np.zeros(N)
    bass = np.zeros(N)
    lead = np.zeros(N)
    fx = np.zeros(N)
    beats, downbeats, hits = [], [], []
    for bar in range(BARS):
        t_bar = bar * 4 * B
        intro = bar < 4
        brk = bar in (12, 13)
        drop = not intro and not brk
        downbeats.append(round(t_bar, 4))
        for b in range(4):
            beats.append(round(t_bar + b * B, 4))
        # cowbell lead (16ths)
        pat = LEAD_B if bar % 2 else LEAD
        for i, n in enumerate(pat):
            if n is None:
                continue
            place(lead, t_bar + i * B / 4, cowbell(n), 0.55 if drop else 0.4)
        if drop:
            for b in range(4):
                if b in (0, 2) or (b == 3 and bar % 2):
                    place(drums, t_bar + b * B, kick(), 1.0)
                    hits.append(round(t_bar + b * B, 4))
                if b in (1, 3):
                    place(drums, t_bar + b * B, clap(), 0.65)
                for h in range(2):
                    place(drums, t_bar + b * B + h * B / 2, hat(open_=(h == 1 and b == 3)), 0.22)
            if bar % 4 == 3:                         # hi-hat roll into the next bar
                for r in range(8):
                    place(drums, t_bar + 3 * B + r * B / 8, hat(), 0.18 + r * 0.02)
            for (n, beat, ln) in BASS:
                place(bass, t_bar + beat * B, bass808(n, ln * B), 0.9)
        if bar == 3:
            place(fx, t_bar, riser(4 * B), 0.5)
        if bar == 13:
            place(fx, t_bar, riser(4 * B), 0.45)
    place(fx, 0, crackle(TOTAL), 0.12)
    # sidechain pump: duck bass + lead under each kick
    pump = np.ones(N)
    for h in hits:
        i0 = int(h * SR)
        L = int(0.22 * SR)
        pump[i0:i0 + L] = np.minimum(pump[i0:i0 + L], 0.35 + 0.65 * np.linspace(0, 1, len(pump[i0:i0 + L])))
    intro_end = int(4 * 4 * B * SR)
    lead_f = lead.copy()
    lead_f[:intro_end] = lp(lead[:intro_end], 1400)            # muffled intro
    mix = drums * 0.9 + bass * pump * 0.8 + lead_f * pump * 0.6 + fx
    mix = np.stack([mix, mix], 1)
    wet = reverb(lead_f * 0.3, IR_ROOM, 0.5)[:N]
    mix += wet * 0.35
    # tape stop on the last beat
    ts = int((BARS * 4 - 1) * B * SR)
    seg = mix[ts:ts + int(B * SR) * 2]
    k = np.cumsum(np.linspace(1, 0.05, len(seg)))
    k = np.clip(k.astype(int), 0, len(seg) - 1)
    mix[ts:ts + len(seg)] = seg[k] * np.linspace(1, 0, len(seg))[:, None]
    mix[ts + len(seg):] = 0
    mix = np.tanh(mix * 1.3) / np.tanh(1.3)
    mix = mix / np.max(np.abs(mix)) * 0.95
    os.makedirs(OUT, exist_ok=True)
    wavfile.write(os.path.join(OUT, 'phonk.wav'), SR, (mix * 32767).astype(np.int16))
    grid = dict(bpm=BPM, beat=B, beats=beats, downbeats=downbeats, kicks=hits, drop1=round(4 * 4 * B, 4),
                break_=round(12 * 4 * B, 4), drop2=round(14 * 4 * B, 4), end=round(BARS * 4 * B, 4))
    json.dump(grid, open(os.path.join(OUT, 'beats.json'), 'w'), indent=1)
    print('phonk', round(TOTAL, 2), 's; drop at', grid['drop1'], 's; break', grid['break_'], '; drop2', grid['drop2'])


if __name__ == '__main__':
    build()
