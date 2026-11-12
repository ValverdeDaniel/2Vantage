"""The comparison half of the Fidelity lane, inside the parity tools image: every deal folder the fetch wrote, each
file pair compared, the differences labelled from the register, then report.md and differences.json written.

Per file: the file name each app gave (masked; J104), then the files themselves. A file one app refuses and the
other builds is one difference; both refusing is a match (each refusal's words are listed in the report).
"""

import json
import tempfile
from pathlib import Path

from . import intended, mask, pdf, pptx, report, xlsx

COMPARERS = {
    'xlsx': lambda old, new, work: xlsx.compare(old, new),
    'pdf': lambda old, new, work: pdf.compare(old, new, work),
    'pptx': lambda old, new, work: pptx.compare(old, new),
}


def _name(entry):
    return mask.line((entry or {}).get('name') or '') or None


def _pair(folder, record, kind, work):
    old_entry = record['files'].get(f'old.{kind}') or {}
    new_entry = record['files'].get(f'new.{kind}') or {}
    old_ok, new_ok = old_entry.get('status') == 200, new_entry.get('status') == 200
    if not old_ok or not new_ok:
        if old_ok == new_ok:
            return [], 'both refused'
        return [{
            'where': 'file', 'kind': 'refused',
            'old': old_entry.get('refused') or old_entry.get('status'),
            'new': new_entry.get('refused') or new_entry.get('status'),
        }], 'one refused'  # fmt: skip
    found = []
    if _name(old_entry) != _name(new_entry):
        found.append({'where': 'file name', 'kind': 'file-name', 'old': _name(old_entry), 'new': _name(new_entry)})
    found.extend(COMPARERS[kind](folder / f'old.{kind}', folder / f'new.{kind}', work))
    return found, 'compared'


def compare(folder, register):
    entries = intended.load(register)
    results = []
    with tempfile.TemporaryDirectory() as scratch:
        for deal_folder in sorted(path for path in folder.iterdir() if (path / 'fetch.json').exists()):
            record = json.loads((deal_folder / 'fetch.json').read_text(encoding='utf-8'))
            for kind in ('xlsx', 'pdf', 'pptx'):
                work = Path(scratch) / deal_folder.name / kind
                found, state = _pair(deal_folder, record, kind, work)
                intended.label(entries, deal_folder.name, kind, found)
                results.append({'deal': deal_folder.name, 'file': kind, 'state': state, 'differences': found})
                counts = report.counts(found)
                print(f'{deal_folder.name} {intended.FILES[kind]:<13} {state:<12} '
                      f'{counts["differences"]:>5} differences: {counts["intended"]:>5} intended, '
                      f'{counts["unexplained"]:>5} unexplained')  # fmt: skip
    unused = [entry for entry in entries if not entry.get('used')]
    report.write(folder, results, entries, unused)
    unexplained = sum(report.counts(r['differences'])['unexplained'] for r in results)
    print(f'Report: {folder / "report.md"} ({unexplained} unexplained; {len(unused)} register entries matched nothing)')
    return 1 if unexplained else 0
