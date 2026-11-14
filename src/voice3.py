"""Voice processing for 'Поезд в 03:17': narration clips, whisper / phone effects, the double's creepy line."""
import os
import subprocess
import numpy as np
from scipy import signal
from audio import SR, lp, hp, bp, norm, reverb, IR_STAIR, IR_ROOM, ir
import timeline3 as TL

IR_TRAIN = ir(1.2, 0.01, 7, 3500)


def load_part(part):
    p = os.path.join(TL.ADIR, f'part{part}.mp3')
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float64) / 32768


def fade_edges(x, ms=12):
    n = int(SR * ms / 1000)
    if len(x) > 2 * n:
        x = x.copy()
        x[:n] *= np.linspace(0, 1, n)
        x[-n:] *= np.linspace(1, 0, n)
    return x


def env_follow(x, ms=15):
    win = max(1, int(SR * ms / 1000))
    return np.convolve(np.abs(x), np.ones(win) / win, 'same')


def whisper_fx(x):
    """Breathy whisper of the narrator's own voice (the double whispers)."""
    rng = np.random.default_rng(5)
    e = env_follow(hp(x, 1500), 10)
    breath = bp(rng.standard_normal(len(x)), 1200, 7000) * e * 3.0
    dry = hp(x, 400) * 0.55
    y = norm(dry + norm(breath) * 0.5) * 0.8
    st = reverb(y, IR_ROOM, 0.35)[:len(x) + int(0.4 * SR)]
    return st


def phone_fx(x):
    y = bp(x, 320, 3300, 4)
    y = np.tanh(y * 3.0) / 1.2
    y = np.round(y * 64) / 64                                         # light bit-crush
    rng = np.random.default_rng(3)
    y = y + bp(rng.standard_normal(len(y)), 1000, 4000) * 0.012       # line hiss
    y = norm(y) * 0.85
    return np.stack([y, y], 1)


def pitch_resample(x, semis):
    f = 2 ** (semis / 12)
    n = int(len(x) / f)
    return signal.resample(x, n)


def double_line():
    """'Ну что, поехали ещё раз?' — synthesized (espeak-ng), slowed, doubled and whispered: an inhuman copy of you."""
    from tts_espeak import synth
    x, sr = synth('Ну что... поехали... ещё раз?', rate=80, pitch=20, wordgap=3)
    x = signal.resample(x.astype(np.float64), int(len(x) * SR / sr))
    x = x / (np.max(np.abs(x)) + 1e-9)
    low = pitch_resample(x, -1.5)
    n = len(low)
    t = np.arange(n) / SR
    rng = np.random.default_rng(9)
    e = env_follow(low, 12)
    whisper = bp(rng.standard_normal(n), 1500, 7500) * e * 4
    twin = pitch_resample(x, -1.1)[:n]                      # a second voice, slightly out of tune
    twin = np.pad(twin, (int(0.025 * SR), 0))[:n]
    twin = np.pad(twin, (0, n - len(twin)))
    sub = pitch_resample(x, -13.5)[:n]                      # an octave below, under everything
    sub = np.pad(sub, (0, n - len(sub)))
    y = (norm(low) + norm(twin) * 0.18 + norm(whisper) * 0.1 + norm(low * np.sin(2 * np.pi * 38 * t)) * 0.04 +
         norm(lp(sub, 900)) * 0.0)
    y = fade_edges(norm(np.tanh(norm(y) * 1.15)) * 0.9, 25)
    st = reverb(y, IR_TRAIN, 0.2)
    return st[:n + int(0.8 * SR)]


if __name__ == '__main__':
    d = double_line()
    print('double line seconds', round(len(d) / SR, 2), 'speech', round((len(d) - 0.8 * SR) / SR, 2))
    from scipy.io import wavfile
    os.makedirs(os.path.join(TL.ROOT, 'build', 'train'), exist_ok=True)
    wavfile.write(os.path.join(TL.ROOT, 'build', 'train', 'double_line.wav'), SR, (np.clip(d, -1, 1) * 32767).astype(np.int16))
