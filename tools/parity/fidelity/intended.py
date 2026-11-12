"""The register of intended differences (`tools/parity/intended.yaml`; plan.md §12.7, Q.5 "Judging"): read, and
held against the differences found, so each is labelled with the item that causes it or left unexplained.

The register is a small YAML subset, read here without PyYAML (the tools image has none): `intended:` then a list of
flat entries, each `- key: value` then `  key: value`, the values plain, "double-" or 'single-quoted', or null; `#`
starts a comment outside quotes. An entry covers a difference when every matcher it gives agrees:

- `deal`: GD1, a list "GD1, GD3", or all;
- `file`: workbook | proposal-pdf | deck | paper (the files this lane compares; paper is the Letter PDF), or a list
  ("proposal-pdf, paper": Paper is the PDF's pages on Letter, read back at the page's size, so one entry fits both);
- `where`: a glob over the difference's place ("Medical!B12", "page 6 «Dental — Delta Dental»", "slide 3 *"), or
  all;
- `kind` (optional): a glob or a list over its kind (value, formula, row-added, words, run-font, …);
- `match` (optional): a regular expression searched in "<old> → <new>".

`item`, `old`, `new`, `why`, `signed_by` and `signed_on` are what a person reads and signs; they match nothing.
"""

import fnmatch
import re

FILES = {'xlsx': 'workbook', 'pdf': 'proposal-pdf', 'pptx': 'deck', 'letter': 'paper'}
_KEY = re.compile(r'^(-\s+)?([A-Za-z_]+):\s*(.*)$')


def _scalar(raw):
    raw = raw.strip()
    if raw.startswith('"'):
        end, out, i = None, [], 1
        while i < len(raw):
            ch = raw[i]
            if ch == '\\' and i + 1 < len(raw):
                out.append({'n': '\n', 't': '\t'}.get(raw[i + 1], raw[i + 1]))
                i += 2
                continue
            if ch == '"':
                end = i
                break
            out.append(ch)
            i += 1
        if end is None:
            raise ValueError(f'unclosed quote: {raw}')
        return ''.join(out)
    if raw.startswith("'"):
        end = raw.find("'", 1)
        while end != -1 and raw[end + 1 : end + 2] == "'":
            end = raw.find("'", end + 2)
        if end == -1:
            raise ValueError(f'unclosed quote: {raw}')
        return raw[1:end].replace("''", "'")
    raw = raw.split(' #', 1)[0].strip()
    if raw in ('', 'null', '~'):
        return None
    if raw == '[]':
        return []
    return raw


def load(path):
    entries, current = [], None
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        match = _KEY.match(stripped)
        if match is None:
            raise ValueError(f'{path.name}:{number}: not "key: value": {line}')
        dash, key, value = match.groups()
        if key == 'intended' and not dash and current is None and not line.startswith(' '):
            continue
        if dash:
            current = {'line': number}
            entries.append(current)
        if current is None:
            raise ValueError(f'{path.name}:{number}: a key outside an entry: {line}')
        current[key] = _scalar(value)
    for entry in entries:
        missing = [key for key in ('item', 'deal', 'file', 'where', 'why') if not entry.get(key)]
        if missing:
            raise ValueError(f'{path.name}:{entry["line"]}: the entry has no {", ".join(missing)}')
    return entries


def _listed(value, wanted):
    if value is None or value == 'all':
        return True
    return any(fnmatch.fnmatchcase(wanted, part.strip()) for part in str(value).split(','))


def covers(entry, deal, file, difference):
    if not _listed(entry.get('deal'), deal) or not _listed(entry.get('file') or '-', FILES.get(file, file)):
        return False
    where = entry.get('where')
    if where != 'all' and not fnmatch.fnmatchcase(difference['where'], where):
        return False
    if entry.get('kind') and not _listed(entry['kind'], difference['kind']):
        return False
    if entry.get('match'):
        text = f'{difference.get("old")} → {difference.get("new")}'
        if re.search(entry['match'], text) is None:
            return False
    return True


def label(entries, deal, file, differences):
    """Each difference gets `status` (intended | unexplained) and, when intended, `item` and `entry` (its line)."""
    for difference in differences:
        hit = next((entry for entry in entries if covers(entry, deal, file, difference)), None)
        difference['status'] = 'intended' if hit else 'unexplained'
        if hit:
            difference['item'], difference['entry'] = hit['item'], hit['line']
            hit['used'] = hit.get('used', 0) + 1
    return differences
