"""'Поезд в 03:17': narration clips (cut at sentence boundaries), pauses for the action, captions."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADIR = os.path.join(ROOT, 'audio', 'train')
WORDS = {int(k): v for k, v in json.load(open(os.path.join(ADIR, 'words.json'))).items()}

HOOK = 5.2          # silent hook: on-screen text over the arriving train (the first line has no voice-over)

# (id, part, first word, last word, pause after, fx)
CLIPS = [
    ('A1', 20, 0, 5, 0.25, None), ('A2', 19, 0, 4, 0.3, None), ('A3', 1, 0, 10, 0.5, None),
    ('A4', 2, 0, 10, 0.7, None),
    ('B1', 3, 2, 5, 0.4, None), ('B2', 4, 0, 2, 0.25, None), ('B3', 4, 3, 14, 0.6, None),
    ('B4', 5, 0, 1, 2.0, None), ('B5', 5, 2, 4, 1.1, None), ('B6', 6, 0, 2, 0.9, None),
    ('B7', 6, 3, 8, 1.8, None), ('B8', 7, 0, 7, 1.4, None), ('B9', 7, 8, 9, 2.0, None),
    ('C1', 8, 3, 10, 0.4, None), ('C2', 9, 0, 3, 0.3, None), ('C3', 9, 4, 11, 0.8, None),
    ('C4', 10, 0, 4, 0.3, None), ('C5', 10, 5, 6, 1.4, None), ('C6', 10, 7, 13, 0.5, None),
    ('C7', 11, 0, 8, 0.35, None), ('C8', 11, 9, 12, 0.3, None), ('C9', 11, 13, 21, 0.8, None),
    ('C10', 12, 0, 8, 0.5, None), ('C11', 12, 9, 14, 1.8, 'whisper'),
    ('D1', 13, 1, 8, 0.25, None), ('D2', 13, 9, 10, 0.2, None), ('D3', 13, 11, 19, 0.15, None),
    ('D4', 13, 20, 25, 0.15, None), ('D5', 14, 0, 12, 0.2, None), ('D6', 14, 13, 20, 0.3, None),
    ('D7', 14, 21, 24, 1.6, None), ('D8', 14, 25, 32, 1.8, None),
    ('E1', 15, 1, 8, 0.5, None), ('E2', 15, 9, 10, 0.4, None), ('E3', 15, 11, 16, 2.2, None),
    ('E4', 15, 17, 18, 0.6, None), ('E5', 15, 19, 21, 0.4, None), ('E6', 15, 22, 27, 0.4, 'phone'),
    ('F1', 16, 0, 1, 0.8, None), ('F2', 16, 2, 6, 0.6, None), ('F3', 16, 7, 15, 0.4, None),
    ('F4', 16, 16, 24, 1.5, None),
    ('G1', 17, 0, 3, 0.4, None), ('G2', 17, 4, 9, 0.35, None), ('G3', 17, 10, 15, 0.4, None),
    ('G4', 17, 16, 20, 0.3, None), ('G5', 17, 21, 23, 1.3, None), ('G6', 17, 24, 29, 0.9, None),
    ('H1', 18, 0, 7, 0.4, None), ('H2', 18, 8, 13, 0.3, None), ('H3', 18, 14, 21, 0.3, None),
    ('H4', 18, 22, 25, 1.4, None), ('H5', 18, 26, 35, 0.4, None), ('H6', 18, 36, 41, 1.6, None),
]
DOUBLE_LINE = 'Ну что, поехали ещё раз?'
# the double's own voice (recorded by the author): audio/train/double/*.mp3
DOUBLE_FILE = 'double/b.mp3'
DOUBLE_DUR = 2.2
DOUBLE_WORDS = [('НУ', 0.0, 0.28), ('ЧТО,', 0.28, 0.5), ('ПОЕХАЛИ', 1.04, 1.46), ('ЕЩЁ', 1.46, 1.68), ('РАЗ?', 1.68, 2.1)]
CLIP_OVERRIDE = {
    'C11': dict(file='double/a.mp3', dur=2.6,
                words=[('«Не', 0.0, 0.3), ('садись.', 0.3, 0.94), ('Ты', 1.34, 1.42), ('уже', 1.42, 1.64),
                       ('здесь', 1.64, 1.9), ('был»', 1.9, 2.3)]),
}
END_HOLD = 5.0          # hard blackout + "КОНЕЦ"

# corrected caption words (ASR mistakes / numbers); None = drop the token
FIX = {(1, 4): 'садились', (2, 2): 'узнаёшь', (2, 9): 'её', (4, 13): '03:16.', (4, 14): None, (5, 1): 'ждёшь.',
       (6, 4): 'из', (6, 5): 'тёмного', (6, 0): 'Становится', (6, 2): 'тихо.', (6, 3): 'И',
       (8, 8): 'неподвижны,', (8, 9): 'словно', (10, 3): 'поднимает', (11, 5): 'худи', (11, 7): 'чёрные',
       (11, 20): '03:17.', (11, 21): None, (12, 3): 'поднимает', (12, 8): 'шепчет:', (12, 9): '«Не', (12, 10): 'садись.',
       (12, 11): 'Ты', (12, 14): 'был»', (13, 14): 'встаёт', (15, 9): 'Достаёшь', (15, 21): 'голос:',
       (15, 22): '«Ты', (15, 27): 'поезде»', (16, 3): 'приходит', (16, 4): 'сообщение', (17, 2): 'поднимаешь',
       (17, 10): 'Но ты', (17, 20): 'написано:', (17, 21): '«ПОСЛЕДНЯЯ', (17, 22): 'СТАНЦИЯ.', (17, 23): '03:17»',
       (17, 29): '03:17.', (18, 4): 'доносится', (18, 8): 'Камера', (18, 24): '03:17.', (18, 25): None,
       (18, 1): None, (18, 0): 'Из-под', (3, 2): 'Ты', (10, 4): 'голову.', (5, 2): 'Вдруг'}


def _clip_bounds(part, i0, i1):
    w = WORDS[part]
    a = max(0.0, w[i0][1] - 0.06)
    if i0 > 0:
        a = max(a, w[i0 - 1][2] + 0.02)
    b = w[i1][2] + 0.14
    if i1 + 1 < len(w):
        b = min(b, w[i1 + 1][1] - 0.02)
    return a, b


CL = {}          # id -> dict(t0, t1, part, src_a, src_b, words=[(word, gt0, gt1)])
_t = HOOK
for cid, part, i0, i1, gap, fx in CLIPS:
    if cid in CLIP_OVERRIDE:
        o = CLIP_OVERRIDE[cid]
        words = [(w, _t + wa, _t + wb) for (w, wa, wb) in o['words']]
        CL[cid] = dict(t0=_t, t1=_t + o['dur'], part=part, src=None, fx=fx, file=o['file'], words=words)
        _t += o['dur'] + gap
        continue
    a, b = _clip_bounds(part, i0, i1)
    words = []
    for i in range(i0, i1 + 1):
        w, wa, wb = WORDS[part][i]
        w = FIX.get((part, i), w)
        if w is None:
            continue
        words.append((w, _t + wa - a, _t + wb - a))
    CL[cid] = dict(t0=_t, t1=_t + (b - a), part=part, src=(a, b), fx=fx, words=words)
    _t += (b - a) + gap
T_DOUBLE = _t + 1.5           # the double's line in the last shot (after a long, silent grin)
T_BLACK = T_DOUBLE + DOUBLE_DUR + 0.25
TOTAL = T_BLACK + END_HOLD


def S(cid):
    return CL[cid]['t0']


def E(cid):
    return CL[cid]['t1']


def W(cid, word, occ=0, end=False):
    n = 0
    for w, a, b in CL[cid]['words']:
        if w.lower().strip('.,!?:;«»"') == word.lower():
            if n == occ:
                return b if end else a
            n += 1
    raise KeyError((cid, word))


HOT = {'исчезает', 'двойник', '03:17', '03:17.', 'кошмар', 'руки', 'рук', 'поезда', 'поезде', 'никогда',
       'выходил', 'тихо', 'останавливаются', 'голову', 'странность', 'часы', 'выглядит', 'ты'}
HOT = {'исчезает', 'двойник', '03:17', 'рук', 'никогда', 'выходил', 'тихо', 'останавливаются', 'странность',
       'возвращались', 'манекены', 'сигнал', 'поезде', 'назад', 'бежишь', 'замираешь'}


def _norm(w):
    return w.lower().strip('.,!?:;«»"')


def caption_chunks():
    chunks = []
    for cid, *_ in CLIPS:
        words = CL[cid]['words']
        cur = []
        for i, (w, a, b) in enumerate(words):
            cur.append((w, a, b))
            chars = sum(len(x[0]) for x in cur)
            brk = w[-1] in '.,!?:»' or len(cur) >= 3 or chars >= 17
            nxt = words[i + 1][0] if i + 1 < len(words) else None
            if not brk and nxt is not None and chars + len(nxt) > 20:
                brk = True
            if i == len(words) - 1:
                chunks.append(cur)
                cur = []
            elif brk:
                if len(_norm(w)) <= 3 and w[-1] not in '.,!?:»' and len(cur) > 1:
                    last = cur.pop()
                    chunks.append(cur)
                    cur = [last]
                else:
                    chunks.append(cur)
                    cur = []
    out = []
    for i, ch in enumerate(chunks):
        start = ch[0][1] - 0.05
        end = ch[-1][2] + 0.35
        if i + 1 < len(chunks):
            end = min(end, chunks[i + 1][0][1] - 0.05)
        out.append(dict(start=start, end=end,
                        words=[(w.strip(',.:').upper(), a, b, _norm(w) in HOT) for (w, a, b) in ch]))
    dw = [(w, T_DOUBLE + a, T_DOUBLE + b, True) for (w, a, b) in DOUBLE_WORDS]
    out.append(dict(start=T_DOUBLE - 0.05, end=T_DOUBLE + 0.95, words=dw[:2]))
    out.append(dict(start=T_DOUBLE + 0.99, end=T_BLACK, words=dw[2:]))
    return out


if __name__ == '__main__':
    print('total', round(TOTAL, 1), 'double at', round(T_DOUBLE, 1))
    for cid, *_ in CLIPS:
        c = CL[cid]
        print(cid, round(c['t0'], 2), round(c['t1'], 2), ' '.join(w for w, a, b in c['words']))
