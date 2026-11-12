"""The Fidelity lane's report: report.md for a person (per deal and file the counts, every unexplained difference,
then the intended ones grouped by their register entry) and differences.json with everything, beside the files."""

import json
from collections import defaultdict

from . import intended

SHOWN = 160  # characters of a value in report.md


def counts(found):
    out = {'differences': len(found), 'intended': 0, 'unexplained': 0}
    for difference in found:
        out[difference.get('status', 'unexplained')] += 1
    return out


def _short(value):
    text = '' if value is None else str(value)
    text = text.replace('|', '¦').replace('\n', ' ')
    return text if len(text) <= SHOWN else text[: SHOWN - 1] + '…'


def write(folder, results, entries, unused):
    (folder / 'differences.json').write_text(json.dumps(results, indent=1, default=str), encoding='utf-8')
    lines = ['# Fidelity: old Vantage against 2Vantage, client files', '']
    lines += ['| Deal | File | State | Differences | Intended | Unexplained |', '|---|---|---|---|---|---|']
    for result in results:
        c = counts(result['differences'])
        file = intended.FILES[result['file']]
        lines.append(f'| {result["deal"]} | {file} | {result["state"]} | {c["differences"]} | {c["intended"]} '
                     f'| {c["unexplained"]} |')  # fmt: skip
    lines += ['', '## Unexplained', '']
    any_left = False
    for result in results:
        left = [d for d in result['differences'] if d.get('status') != 'intended']
        if not left:
            continue
        any_left = True
        lines += [f'### {result["deal"]} · {intended.FILES[result["file"]]} ({len(left)})', '']
        lines += ['| Where | Kind | Old | New |', '|---|---|---|---|']
        lines += [f'| {_short(d["where"])} | {d["kind"]} | {_short(d["old"])} | {_short(d["new"])} |' for d in left]
        lines.append('')
    if not any_left:
        lines += ['None.', '']
    by_entry = defaultdict(list)
    for result in results:
        for difference in result['differences']:
            if difference.get('status') == 'intended':
                by_entry[difference['entry']].append((result['deal'], result['file'], difference))
    lines += ['## Intended, by register entry', '']
    for entry in entries:
        found = by_entry.get(entry['line'], [])
        if not found:
            continue
        deals = sorted({deal for deal, _file, _d in found})
        lines.append(f'- **{entry["item"]}** ({entry["file"]}, {", ".join(deals)}; {len(found)}): {entry["why"]}')
    if unused:
        lines += ['', '## Register entries that matched nothing', '']
        lines += [f'- line {e["line"]}: {e["item"]} · {e["deal"]} · {e["file"]} · {e["where"]}' for e in unused]
    (folder / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
