"""«Крик» (decibel escalation short): stage layout."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = os.path.join(ROOT, 'audio', 'db', 'b.mp3')        # the author's only line: «ИДИ НАХУЙ!»
STAGE = 8.2
SHOUT_AT = 0.55                                            # voice starts this long after a stage begins
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
TOTAL = STAGE * len(STAGES)


def stage_at(t):
    k = min(len(STAGES) - 1, max(0, int(t // STAGE)))
    return k, t - k * STAGE


def fmt(n):
    s = f'{n:,}'.replace(',', ' ')
    return s
