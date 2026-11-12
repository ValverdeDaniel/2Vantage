"""Is this census one row per benefit? (plan.md §5.3.2 step 3; C13). Pure.

Ported from old Vantage 891f1b3 `market/census_pivot.py` (`detect_shape` and its helpers), unchanged in its rules:
a column naming the benefit on each row, people repeated across rows with the same demographics, and one generic
plan/tier column pair raise the score; headers that already name two lines, or every row a different person, lower
it. Plan-design names (PPO, HMO, HDHP…) are deliberately not benefit labels: a normal roster's plan column is full of
them, and reading them as benefits would merge two people into one row.
"""

import re

# >= CONFIDENT: reformat automatically. Between SUSPECT and CONFIDENT: "needs attention" (Claude's classifier is
# slice 51's; without it the member maps by hand).
CONFIDENT = 0.80
SUSPECT = 0.55

# A benefit label on a row -> the line it names (§4.1 keys).
LINE_LABELS = {
    'medical': 'medical', 'med': 'medical', 'health': 'medical', 'major medical': 'medical', 'medical plan': 'medical',
    'dental': 'dental', 'dent': 'dental',
    'vision': 'vision',
    'basic life': 'basic_life_add', 'life': 'basic_life_add', 'basic life add': 'basic_life_add',
    'life add': 'basic_life_add', 'basic life and add': 'basic_life_add', 'group life': 'basic_life_add',
    'voluntary life': 'voluntary_life', 'vol life': 'voluntary_life', 'supplemental life': 'voluntary_life',
    'supp life': 'voluntary_life', 'employee life': 'voluntary_life',
    'std': 'std', 'short term disability': 'std', 'short term': 'std',
    'ltd': 'ltd', 'long term disability': 'ltd', 'long term': 'ltd',
}  # fmt: skip

# Headers that announce a benefit-per-row column outright.
LINE_COLUMN_HEADERS = (
    'benefit', 'benefit type', 'benefit plan', 'coverage', 'coverage type', 'plan type', 'product', 'line',
    'line of coverage', 'benefit line',
)  # fmt: skip

# Each line's block once reshaped; the labels are ones the mapper reads exactly (§4.8), so nothing needs checking.
LINE_OUTPUT_COLUMNS = {
    'medical': [('plan', 'Medical Plan'), ('tier', 'Medical Tier'), ('effective', 'Medical Effective Date')],
    'dental': [('plan', 'Dental Plan'), ('tier', 'Dental Tier'), ('effective', 'Dental Effective Date')],
    'vision': [('plan', 'Vision Plan'), ('tier', 'Vision Tier'), ('effective', 'Vision Effective Date')],
    'basic_life_add': [('amount', 'Basic Life Amount'), ('effective', 'Basic Life Effective Date')],
    'voluntary_life': [('amount', 'Voluntary Life Insurance'), ('effective', 'Vol Life Effective Date')],
    'std': [('amount', 'STD Benefit Amount'), ('effective', 'STD Effective Date')],
    'ltd': [('amount', 'LTD Benefit Amount'), ('effective', 'LTD Effective Date')],
}

HEADER_LINE_TOKENS = ('medical', 'dental', 'vision', 'life', 'std', 'ltd')
RELATIONSHIP_HEADERS = (
    'rel', 'relationship', 'relation', 'rel code', 'relationship code', 'member type', 'dependent type',
)  # fmt: skip
EMP_ID_HEADERS = (
    'emp no', 'emp id', 'employee id', 'employee number', 'employee no', 'eid', 'subscriber id', 'member id',
)  # fmt: skip
# Columns whose value must agree across one person's rows; a disagreement means the key merged two people.
IDENTITY_HINTS = ('first name', 'last name', 'middle name', 'name', 'dob', 'date of birth', 'birth', 'gender', 'sex')


def squash(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', str(text or '').lower()).strip())


def digits(text):
    return re.sub(r'\D', '', str(text or ''))


def cell(row, column):
    if column is None or column >= len(row):
        return ''
    return str(row[column] or '').strip()


def label_to_line(raw):
    """A benefit label's line key, or '' when it is not recognized (longest phrase first: 'voluntary life')."""
    words = squash(raw)
    if not words:
        return ''
    if words in LINE_LABELS:
        return LINE_LABELS[words]
    for phrase in sorted(LINE_LABELS, key=len, reverse=True):
        if re.search(rf'\b{re.escape(phrase)}\b', words):
            return LINE_LABELS[phrase]
    return ''


def column_role(header):
    """Which slot of a line's block a column fills: tier, plan, effective, amount or ''."""
    if 'tier' in header or 'coverage level' in header or header in ('coverage', 'election', 'coverage election'):
        return 'tier'
    if 'plan' in header:
        return 'plan'
    if 'effective' in header or 'eff date' in header:
        return 'effective'
    if 'amount' in header or 'volume' in header:
        return 'amount'
    return ''


def _find(headers, candidates):
    return next((i for i, header in enumerate(headers) if header in candidates), None)


def line_column(headers, rows):
    """(column | None, {label: line}, recognized ratio, named outright): the column naming each row's benefit."""
    words = [squash(header) for header in headers]
    best = (None, {}, 0.0, False)
    for col in range(len(headers)):
        if column_role(words[col]) == 'plan':  # a plan column is never the benefit column
            continue
        values = [row[col] for row in rows if col < len(row) and str(row[col]).strip()]
        distinct = list(dict.fromkeys(values))
        if not distinct or len(distinct) > 12:
            continue
        labels = {value: label_to_line(value) for value in distinct if label_to_line(value)}
        ratio = len(labels) / len(distinct)
        named = words[col] in LINE_COLUMN_HEADERS
        if ratio < (0.01 if named else 0.70):
            continue
        if ratio + (0.1 if named else 0) > best[2] + (0.1 if best[3] else 0):
            best = (col, labels, ratio, named)
    return best


def person_columns(headers):
    """The columns that identify a person — never the employee id alone, which a whole family shares."""
    words = [squash(header) for header in headers]
    ssn_cols = [i for i, header in enumerate(words) if 'ssn' in header or 'social' in header]
    own = next(
        (i for i in ssn_cols if not any(w in words[i] for w in ('employee', 'subscriber', 'primary', 'ee '))),
        ssn_cols[0] if ssn_cols else None,
    )
    return {
        'ssn': own,
        'first': _find(words, ('first name', 'first', 'fname', 'employee first name', 'member first name')),
        'last': _find(words, ('last name', 'last', 'lname', 'employee last name', 'member last name')),
        'dob': _find(words, ('dob', 'date of birth', 'birth date', 'birthdate', 'birthday')),
        'relationship': _find(words, RELATIONSHIP_HEADERS),
        'emp_id': _find(words, EMP_ID_HEADERS),
    }


def person_key(row, cols):
    """A stable identity for one row, or '' when it cannot be told."""
    ssn = digits(cell(row, cols['ssn']))
    if ssn:
        return f'ssn:{ssn}'
    parts = [squash(cell(row, cols[key])) for key in ('last', 'first', 'dob')]
    return 'name:' + '|'.join(parts) if any(parts) else ''


def _repeats(headers, rows, keys):
    """(score, signals) from people repeated across rows with the same demographics."""
    words = [squash(header) for header in headers]
    found = [key for key in keys if key]
    distinct = set(found)
    if not found:
        return 0.0, []
    per_key = len(found) / len(distinct)
    if len(distinct) < 0.75 * len(rows) and per_key >= 1.5:
        score, signals = 0.35, [f'{len(distinct)} people across {len(rows)} rows ({per_key:.1f} rows each)']
        identity = [i for i, header in enumerate(words) if any(hint in header for hint in IDENTITY_HINTS)]
        seen, same = {}, True
        for key, row in zip(keys, rows, strict=True):
            if not key:
                continue
            snapshot = tuple(squash(cell(row, i)) for i in identity)
            if seen.setdefault(key, snapshot) != snapshot:
                same = False
                break
        if same:
            score += 0.10
            signals.append('repeated rows carry identical demographics')
        return score, signals
    if len(distinct) == len(rows):
        return -0.40, ['every row is a different person']
    return 0.0, []


def detect(headers, rows):
    """The shape's score and what it found: {confidence, signals, line_column, line_column_header, label_map,
    unknown_labels}."""
    signals, score = [], 0.0
    words = [squash(header) for header in headers]
    col, labels, ratio, named = line_column(headers, rows)
    if col is not None:
        score += 0.45
        signals.append(f"column '{headers[col]}' holds benefit names ({round(ratio * 100)}% recognized)")
        if named:
            score += 0.10
            signals.append('its header reads like a benefit column')
    keys = [person_key(row, person_columns(headers)) for row in rows]
    more, said = _repeats(headers, rows, keys)
    score += more
    signals += said
    roles = [column_role(header) for header in words]
    tokens = {token for header in words for token in HEADER_LINE_TOKENS if re.search(rf'\b{token}\b', header)}
    if roles.count('plan') == 1 and roles.count('tier') == 1 and not tokens:
        score += 0.10
        signals.append('a single generic plan/tier column pair')
    if len(tokens) >= 2:
        score -= 0.60
        signals.append(f'headers already name separate lines ({", ".join(sorted(tokens))})')
    unknown = []
    if col is not None:
        for row in rows:
            value = cell(row, col)
            if value and value not in labels and value not in unknown:
                unknown.append(value)
    return {
        'confidence': round(max(0.0, min(1.0, score)), 3),
        'signals': signals,
        'line_column': col,
        'line_column_header': headers[col] if col is not None else '',
        'label_map': labels,
        'unknown_labels': unknown,
    }
