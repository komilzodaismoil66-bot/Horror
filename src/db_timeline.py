"""«Крик» (decibel escalation short): stage layout."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = os.path.join(ROOT, 'audio', 'db', 'b.mp3')        # the author's only line: «ИДИ НАХУЙ!»
STAGE = 5.4
SHOUT_AT = 0.4                                             # voice starts this long after a stage begins
SPD = (8.2 - 0.55) / (STAGE - SHOUT_AT)                    # events inside a stage play this much faster
INTER = 2.8                                                # "no sound in space" card before the space stages
SPACE_FROM = 8
STAGES = [
    (20, 'Трава слегка колышется.'),
    (40, 'Листья на деревьях шелестят.'),
    (80, 'Птицы взлетают с деревьев.'),
    (160, 'Деревья начинают трястись.'),
    (320, 'Земля покрывается трещинами.'),
    (640, 'Динозавры в панике убегают.'),
    (1280, 'Горы начинают разрушаться.'),
    (2560, 'Земля раскаляется, океаны испаряются.'),
    (5120, 'Планета начинает раскалываться.'),
    (10240, 'Энергетическая волна распространяется через космос.'),
    (20480, 'Вся галактика оказывается под ударом.'),
]
TOTAL = STAGE * len(STAGES) + INTER


def stage_start(k):
    return k * STAGE + (INTER if k >= SPACE_FROM else 0.0)


def stage_at(t):
    """(stage index, local time); index -1 = the 'no sound in space' card."""
    t_int = SPACE_FROM * STAGE
    if t_int <= t < t_int + INTER:
        return -1, t - t_int
    if t >= t_int + INTER:
        t -= INTER
    k = min(len(STAGES) - 1, max(0, int(t // STAGE)))
    return k, t - k * STAGE


def fmt(n):
    s = f'{n:,}'.replace(',', ' ')
    return s
