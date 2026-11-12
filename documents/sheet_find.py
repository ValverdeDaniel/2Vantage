"""The cell a value was read from, found again in its spreadsheet (plan.md §7.4; E28, D-119, D-122).

`POST documents/{id}/sheet/find/` posts `{value, line, hint}`, never in a URL (values can be census data, Q.8):
`line` is the reader's line (the cell text it saw), tried first; then the value itself. Numbers compare as numbers
("$7,350" finds 7350), dates as dates ("01/01/2026" finds a date cell). An exact cell beats one that only contains the
text ("$1,500 / $3,000" for 1500), which beats a number inside words ("Gold 1500"); within a tier, the cell whose row
or column holds most of `hint`'s words (the plan's carrier and name) wins. Ported from the old sheet_preview.find_cell.
Pure: rows in, a cell out.
"""

import datetime
import re

from .sheets import column_letter, load_sheets

_NUM = re.compile(r'^\(?-?[$€£]?\s*-?[\d,]*\.?\d+\s*%?\)?$')
_TOKEN = re.compile(r'\(?-?[$€£]?\s*-?\d[\d,]*(?:\.\d+)?\s*%?\)?')  # one printed number inside a longer cell
_LETTERS = re.compile(r'[a-z]{2,}', re.I)
_DATE_FORMATS = ('%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%m-%d-%Y')
EXACT_TIER, CONTAINS_TIER, WORDY_TIER = 1000, 100, 0


def number(text):
    """The number a cell says, or None: "$7,350.00" and "7350" are the same; "(25)" is -25."""
    s = (text or '').strip()
    if not s or not _NUM.match(s):
        return None
    negative = (s.startswith('(') and s.endswith(')')) or '-' in s
    try:
        value = float(re.sub(r'[^\d.]', '', s))
    except ValueError:
        return None
    return -value if negative else value


def _norm(text):
    return re.sub(r'\s+', ' ', (text or '').strip().lower())


def _date(text):
    s = (text or '').strip()
    if not s or len(s) > 10 or not s[0].isdigit():
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _exact(cell, text, num, day):
    if num is not None:
        found = number(cell)
        if found is not None and abs(found - num) < 0.005:
            return True
    if day is not None and _date(cell) == day:
        return True
    return _norm(cell) == text


def _contains(cell, text, num):
    if num is not None:
        return any(
            (found := number(token.strip())) is not None and abs(found - num) < 0.005 for token in _TOKEN.findall(cell)
        )
    return len(text) >= 3 and text in _norm(cell)


def _hint_words(hint):
    return [word for word in re.findall(r'[a-z0-9]+', (hint or '').lower()) if len(word) >= 3]


def find_cell(sheets, find, hint=''):
    """{'sheet', 'row', 'col', 'cell'} (0-based row and column, A1 cell) or None."""
    text = _norm(find)
    if not text:
        return None
    num = number(find)
    day = _date(find) if num is None else None
    words = _hint_words(hint)
    best, best_score = None, -1
    for sheet in sheets:
        rows, lowered = sheet['rows'], None
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                if not cell:
                    continue
                if _exact(cell, text, num, day):
                    score = EXACT_TIER
                elif _contains(cell, text, num):
                    score = WORDY_TIER if _LETTERS.search(cell) else CONTAINS_TIER
                else:
                    continue
                if words:
                    lowered = lowered or [[value.lower() for value in line] for line in rows]
                    in_row = ' '.join(lowered[r])
                    in_col = ' '.join(line[c] if c < len(line) else '' for line in lowered)
                    score += max(sum(w in in_row for w in words), sum(w in in_col for w in words))
                if score > best_score:
                    best, best_score = (sheet['name'], r, c), score
    if best is None:
        return None
    name, r, c = best
    return {'sheet': name, 'row': r, 'col': c, 'cell': f'{column_letter(c)}{r + 1}'}


def find_value(filename, raw, value, line='', hint=''):
    """{sheet, cell (A1), state}: the reader's line first, then the value; 'found', or 'absent' with no cell."""
    sheets = load_sheets(filename, raw)
    match = find_cell(sheets, line, hint) if line else None
    if match is None and value and _norm(value) != _norm(line):
        match = find_cell(sheets, value, hint)
    if match is None:
        return {'sheet': None, 'cell': None, 'state': 'absent'}
    return {'sheet': match['sheet'], 'cell': match['cell'], 'state': 'found'}
