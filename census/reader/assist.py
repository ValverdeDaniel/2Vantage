"""Claude's mapping assist (plan.md §4.8, §5.3.2 step 4, §10.4, §10.8; C14, D109; slice 51).

When the offline mapper (C14) leaves a census spreadsheet's columns unmapped or doubted, Claude is asked to propose
their census columns from the headers and each column's value SHAPES only — "9 digits", "a date", "2 letters", "a
number", "text, 2 words" — never a value: names, SSNs and birth dates never reach the model (the old mapper sent 15
raw rows, B14). It never replaces the offline mapper: it proposes only for the columns asked about, only census columns
no other column holds, and every proposal shows as "Check" in the mapping dialog for a person to confirm.

`shape(text)` and `shapes(table, column)` are pure, `ask(job, file, table, mapping, progress)` makes the one call and
`proposed(mapping, headers, answer)` folds its answer in.
"""

import json
import re
from collections import Counter

from django.conf import settings

from .. import fields
from ..importer.mapping import entry
from ..importer.words import LOW_BELOW
from ..values import parse_date

VERSION = 1
ASSISTED = 0.80  # an assisted column's confidence at most: always under LOW_BELOW, so the dialog says Check
MAX_TOKENS = 16_000
SHOWN = 2  # the commonest shapes said per column

_DATE = re.compile(r'^\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}$')
_MONEY = re.compile(r'^\$?-?[\d,]+\.\d{2}$|^\$-?[\d,]+$')
_PERCENT = re.compile(r'^-?\d+(\.\d+)?\s*%$')
_DECIMAL = re.compile(r'^-?\d+\.\d+$')
_LETTERS = re.compile(r'^[A-Za-z]+$')
_WORDS = re.compile(r"^[A-Za-z][A-Za-z .,'&()/-]*$")


def shape(text):
    """A value's shape in words, never the value: what a mapping needs."""
    text = str(text or '').strip()
    if not text:
        return 'blank'
    if _DATE.match(text) and parse_date(text):
        return 'a date'
    if _PERCENT.match(text):
        return 'a percent'
    if _MONEY.match(text):
        return 'an amount'
    if _DECIMAL.match(text):
        return 'a decimal number'
    numeric = re.sub(r'[\s-]', '', text)
    if numeric.isdigit():
        grouped = '' if numeric == text else ' with dashes or spaces'
        return f'{len(numeric)} digit{"s" if len(numeric) != 1 else ""}{grouped}'
    masked = re.sub(r'[\s-]', '', text)
    if re.fullmatch(r'[*xX#•]+\d{4}', masked):
        return 'a masked number ending in 4 digits'
    if _LETTERS.match(text):
        return f'{len(text)} letter{"s" if len(text) != 1 else ""}' if len(text) <= 4 else 'a word'
    if _WORDS.match(text):
        words = len(text.split())
        return 'a word' if words == 1 else f'text, {min(words, 6)}{"+" if words > 6 else ""} words'
    if any(char.isdigit() for char in text) and any(char.isalpha() for char in text):
        return 'letters and digits'
    return 'other text'


def shapes(table, column):
    """'9 digits (98 of 100), blank (2)': a column's commonest shapes, counted. Never a value."""
    found = Counter(shape(row[column] if column < len(row) else '') for row in table.rows)
    filled = sum(count for name, count in found.items() if name != 'blank')
    said = [f'{name} ({count} of {len(table.rows)})' for name, count in found.most_common() if name != 'blank']
    if not filled:
        return 'every row blank'
    return ', '.join(said[:SHOWN]) + (', and other shapes' if len(said) > SHOWN else '')


def asked(mapping):
    """The columns the assist is asked about: unmapped, or mapped below the dialog's Check line."""
    return [item['column'] for item in mapping if not item['field'] or item['confidence'] < LOW_BELOW]


PROMPT = """You map the columns of an employer's census spreadsheet to a benefits census schema. You are shown the \
header row and, for each column, the SHAPES of its values ("9 digits", "a date", "2 letters", "text, 2 words"), never \
the values. For each column you are asked about, pick the census column it holds, or '' when none applies.

Rules:
- Use each census column at most once, and never one another column already holds (listed as taken).
- confidence is 0.0-1.0: high only when the header clearly names the column; use the shapes to tell close ones \
apart (a column of 9 digits is likely ssn; 2 or 3 letters under a coverage header is likely a tier).
- Paired SSN columns: when an employee or subscriber SSN column sits beside a dependent or member SSN column, the \
employee one is subscriber_ssn and the member one is ssn. A lone SSN column is ssn.
- A bare "Effective Date" belongs to the coverage of the column just before it, at confidence 0.7 or lower.
- Do not map totals, counters or blank columns.

Census columns (key = label):
""" + '\n'.join(f'- {field["key"]} = {field["label"]}' for field in fields.FIELDS)

SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['columns'],
    'properties': {
        'columns': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['column', 'field', 'confidence'],
                'properties': {
                    'column': {'type': 'integer'},
                    'field': {'type': 'string', 'enum': [*fields.KEYS, '']},
                    'confidence': {'type': 'number'},
                },
            },
        }
    },
}


def question(table, mapping, columns):
    """The one message the assist sends: headers, shapes, what is taken, what to map. Never a value."""
    from documents.sheets import column_letter

    lines = ["The census spreadsheet's columns (number, letter, header, value shapes):"]
    for item in mapping:
        column = item['column']
        header = ' '.join(str(item['header'] or '').split())[:80] or '(no header)'
        lines.append(f'{column}. {column_letter(column)} "{header}": {shapes(table, column)}')
    taken = [
        f'{item["field"]} (column {item["column"]})'
        for item in mapping
        if item['column'] not in columns and item['field']
    ]
    lines.append('')
    lines.append('Taken already: ' + (', '.join(taken) if taken else 'none'))
    lines.append('Map these columns: ' + ', '.join(str(column) for column in columns))
    return '\n'.join(lines)


def proposed(mapping, answer, columns):
    """(the mapping with the assist's proposals folded in, how many it proposed). Only the asked columns; only census
    columns no other column holds; each at most ASSISTED, so the dialog asks a person to check it."""
    out = [dict(item) for item in mapping]
    held = {item['field'] for item in out if item['field'] and item['column'] not in columns}
    count = 0
    for row in (answer or {}).get('columns') or []:
        column, field = row.get('column'), row.get('field') or ''
        if column not in columns or field not in fields.BY_KEY or field in held:
            continue
        try:
            confidence = max(0.0, min(float(row.get('confidence') or 0), ASSISTED))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence <= 0:
            continue
        index = next(i for i, item in enumerate(out) if item['column'] == column)
        if out[index]['field'] == field and out[index]['confidence'] >= confidence:
            held.add(field)
            continue
        out[index] = {**entry(column, out[index]['header'], field, confidence), 'assist': True}
        held.add(field)
        count += 1
    for item in out:  # a field the assist moved to another column leaves the column that only guessed it
        if item['field'] and not item.get('assist') and item['column'] in columns:
            if sum(1 for other in out if other['field'] == item['field']) > 1:
                item.update(entry(item['column'], item['header'], '', 0.0))
    return out, count


def ask(job, file, table, mapping, progress):
    """(the mapping with Claude's proposals, how many it proposed, a finding or ''). One call, shapes only, recorded
    in the ledger against the job."""
    from ai import budget, calls, client

    columns = asked(mapping)
    if not columns or not table.rows:
        return mapping, 0, ''
    text = question(table, mapping, columns)
    params = client.request(
        model=settings.AI_MODEL,
        system=PROMPT,
        content=[{'type': 'text', 'text': text}],
        schema=SCHEMA,
        effort=settings.AI_EFFORT.get('assist', 'low'),
        max_tokens=MAX_TOKENS,
    )
    tokens = int(len(PROMPT + text + json.dumps(SCHEMA)) / budget.CHARS_PER_TOKEN)
    planned = calls.Planned(params, ('census_assist', file.hash, 'columns'), tokens)
    progress.say(f'Asking Claude about {len(columns)} column{"s" if len(columns) != 1 else ""} from their shapes')
    try:
        done = calls.extract(planned, job=job, purpose='census_assist', on_event=progress.beat)
    except budget.OverLimit as exc:
        return mapping, 0, exc.sentence
    if done.error is not None:
        return mapping, 0, 'Claude could not propose the unmapped columns; map them in the dialog.'
    out, count = proposed(mapping, done.data, columns)
    return out, count, ''
