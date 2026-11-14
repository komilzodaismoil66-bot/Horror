"""Episode 2: audio layout, word timings and caption chunks."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPO = 1.08            # voice sped up 8% (pitch preserved) to fit the 70 s target -> audio/ep2/fast/*.wav
WORDS = {int(k): [[w, a / TEMPO, b / TEMPO] for (w, a, b) in v]
         for k, v in json.load(open(os.path.join(ROOT, 'audio', 'ep2', 'words.json'))).items()}
_RAW = {1: 4.519125, 2: 8.59425, 3: 5.328938, 4: 7.62775, 5: 5.799125, 6: 7.471, 7: 4.205688, 8: 6.765688,
        9: 2.0375, 10: 3.552625, 11: 5.06775, 12: 4.911, 13: 5.328938}
DUR = {k: v / TEMPO for k, v in _RAW.items()}
NPARTS = 13
STORY_PARTS = 9          # parts 10-13 are the poll / call to action (no word captions)

GAP_BEFORE = 0.15
GAP_AFTER = {1: 0.15, 2: 0.15, 3: 0.12, 4: 0.2, 5: 0.15, 6: 0.15, 7: 0.35, 8: 0.15, 9: 0.5, 10: 0.15, 11: 0.15,
             12: 0.2, 13: 1.6}

OFF = {}
_t = GAP_BEFORE
for i in range(1, NPARTS + 1):
    OFF[i] = _t
    _t += DUR[i] + GAP_AFTER[i]
TOTAL = _t

FIX = {'тяжелые': 'тяжёлые', 'перевернутую': 'перевёрнутую', 'тяжелую': 'тяжёлую', 'нашел': 'нашёл',
       'рядом,': 'рядом.', 'машины,': 'машины.', 'удаляются,': 'удаляются.'}


def _norm(w):
    return w.lower().strip('.,!?:;«»"')


def T(part, word, occ=0, end=False):
    n = 0
    for w, a, b in WORDS[part]:
        if _norm(w) == _norm(word):
            if n == occ:
                return OFF[part] + (b if end else a)
            n += 1
    raise KeyError((part, word, occ))


HOT = {'монстра', 'монстр', 'шаги', 'обломки', 'шума', 'замираешь', 'руки', 'дышать', 'бункер', 'дверь',
       'безопасности', 'дом', 'темно', 'завален', 'выскакиваешь'}


def caption_chunks():
    chunks = []
    for part in range(1, STORY_PARTS + 1):
        words = [(FIX.get(w, w), OFF[part] + a, OFF[part] + b) for (w, a, b) in WORDS[part]]
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
        out.append(dict(start=start, end=end,
                        words=[(w.strip(',.').upper(), a, b, _norm(w) in HOT) for (w, a, b) in ch]))
    return out


if __name__ == '__main__':
    print('total', round(TOTAL, 2))
    print({k: round(v, 2) for k, v in OFF.items()})
    print(' | '.join(' '.join(w[0] for w in c['words']) for c in caption_chunks()))
