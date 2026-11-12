"""A check problem and the report's digest (K69, K70). Pure.

A problem is `{code, text, count, fix, where?, people?}`: `fix` is where the screen sends the person (`{tab, lens?,
form?, view?}`), `where` the packet row it belongs to (a packet's or a draft's report), `people` up to 20 names for our
own screen (D-143: a file never names anyone; texts carry counts and column names, never a member's value).
`digest` is the `ack` a download sends back: a short hash of the sorted (code, where, text), so a problem that appears
after the modal opened answers 409 with the fresh report (K70; old `export_check._digest`).
"""

import hashlib
import json

MAX_PEOPLE = 20


def problem(code, text, count=0, fix=None, people=None, where=''):
    out = {'code': code, 'text': text, 'count': count, 'fix': fix}
    if people:
        out['people'] = list(people)[:MAX_PEOPLE]
    if where:
        out['where'] = where
    return out


def digest(found):
    rows = sorted((p['code'], p.get('where', ''), p['text']) for p in found)
    return hashlib.sha256(json.dumps(rows).encode('utf-8')).hexdigest()[:16]


def plural(n, one, many):
    return one if n == 1 else many
