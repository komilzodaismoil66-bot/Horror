"""Audio layout, word timings and caption chunks."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = {int(k): v for k, v in json.load(open(os.path.join(ROOT, 'audio', 'words.json'))).items()}
DUR = {1: 18.6775, 2: 16.666063, 3: 10.370563, 4: 1.802438, 5: 12.2775, 6: 8.515875, 7: 12.669375, 8: 8.045688}

# pause after each part (seconds) - room for sound design beats
GAP_BEFORE = 0.8
GAP_AFTER = {1: 0.5, 2: 0.6, 3: 0.5, 4: 1.3, 5: 0.7, 6: 0.5, 7: 0.7, 8: 3.6}

OFF = {}
_t = GAP_BEFORE
for i in range(1, 9):
    OFF[i] = _t
    _t += DUR[i] + GAP_AFTER[i]
TOTAL = _t

FIX = {'огнем.': 'огнём.', 'паники': 'панике', '5': 'пяти', 'шопот': 'шёпот', 'зовет': 'зовёт',
       'четвертого': 'четвёртого', 'обрывается.': 'обрывается!', 'знает': 'знает,', 'его': 'его,'}


def _norm(w):
    return w.lower().strip('.,!?:;«»"')


def T(part, word, occ=0, end=False):
    """Global time of the occ-th occurrence of `word` in `part`."""
    n = 0
    for w, a, b in WORDS[part]:
        if _norm(w) == _norm(word):
            if n == occ:
                return OFF[part] + (b if end else a)
            n += 1
    raise KeyError((part, word, occ))


HOT = {'кошмар', 'огнём', 'существа', 'пасть', 'зубов', 'слухом', 'шёпот', 'крик', 'существо', 'монстр',
       'грохотом', 'тебя', 'темноту', 'обрывается', 'услышал', 'бросается', 'утаскивает', 'огромные', 'глаз',
       'грохота', 'знает', 'бежать', 'кошмар'}


def caption_chunks():
    chunks = []
    for part in range(1, 9):
        words = []
        for (w, a, b) in WORDS[part]:
            w = FIX.get(w, w)
            if part == 2 and w == 'шопот':
                w = 'шёпот'
            words.append((w, OFF[part] + a, OFF[part] + b))
        cur = []
        for i, (w, a, b) in enumerate(words):
            cur.append((w, a, b))
            chars = sum(len(x[0]) for x in cur)
            brk = w[-1] in '.,!?' or len(cur) >= 3 or chars >= 17
            nxt = words[i + 1][0] if i + 1 < len(words) else None
            if not brk and nxt is not None and chars + len(nxt) > 20:
                brk = True
            if i == len(words) - 1:
                chunks.append(cur)
                cur = []
            elif brk:
                if len(_norm(w)) <= 3 and w[-1] not in '.,!?' and len(cur) > 1:
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
        disp = []
        for (w, a, b) in ch:
            clean = w.strip(',.')
            disp.append((clean.upper(), a, b, _norm(w) in HOT))
        out.append(dict(start=start, end=end, words=disp))
    return out


if __name__ == '__main__':
    print('total', TOTAL)
    for k, v in OFF.items():
        print(k, round(v, 2))
    for c in caption_chunks():
        print(round(c['start'], 2), round(c['end'], 2), ' '.join(w[0] for w in c['words']))
