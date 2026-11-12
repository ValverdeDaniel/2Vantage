"""Intake answers: the one cleaner and the shown-when rule (plan.md §5.2; B2, B3, B.6). Pure.

`clean_value` is the one cleaner for the producer, Claude and portal paths (the old app had one for Claude only, so a
producer's typed answer was never checked; B.5). Ported from old Vantage 891f1b3 `market/intake_writes.py`
(`clean_value`, `_match_option`) and `market/intake.py` (`condition_met`), with §5.2's changes: a multi answer is a
list, a number is stored without trailing zeros, and dates are read without dateutil (the formats below).

Readiness (`needed`, contacts, BOR, census, the checklist) joins this module in slice 40.
"""

import datetime
import re
from decimal import Decimal

from . import form

YES = {'yes', 'y', 'true', '1'}
NO = {'no', 'n', 'false', '0'}
NUMBER = re.compile(r'^-?\d+(\.\d+)?$')
FEIN = re.compile(r'^\d{2}-?\d{7}$')
MULTI_SPLIT = re.compile(r'[,;/]|\s+')
MULTI_SHOWN = 12  # the multi refusal names the first options only

# "Any common date, month-first when ambiguous" (§5.2): ISO first, then US numeric, then month names.
DATE_FORMATS = (
    '%Y-%m-%d',
    '%Y/%m/%d',
    '%m/%d/%Y',
    '%m/%d/%y',
    '%m-%d-%Y',
    '%m-%d-%y',
    '%m.%d.%Y',
    '%B %d %Y',
    '%b %d %Y',
    '%d %B %Y',
    '%d %b %Y',
    '%B %d',
)


def parse_date(text):
    """A date from common written forms, else None. Commas and a trailing period on a month name are ignored."""
    value = re.sub(r'\s+', ' ', str(text or '').replace(',', ' ')).strip()
    value = re.sub(r'^([A-Za-z]{3,})\.', r'\1', value)
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
        if fmt == '%B %d':
            return None  # a date with no year is not a date
        return parsed
    return None


def match_option(raw, options):
    """The option `raw` names, matched without case, or None."""
    wanted = str(raw).strip().lower()
    for option in options or []:
        if str(option).strip().lower() == wanted:
            return option
    return None


def _plain_number(text):
    number = format(Decimal(text), 'f')
    if '.' in number:
        number = number.rstrip('0').rstrip('.')
    return '0' if number in ('-0', '') else number


def clean_value(question, raw):
    """(value, error) for one answer. `question` is a form.QUESTIONS entry (or its key). An empty answer is ('', None):
    the key leaves `answers`. A refused answer is (None, the sentence)."""
    if isinstance(question, str):
        question = form.BY_KEY[question]
    label, kind, options = question['label'], question['type'], question.get('options') or []
    if isinstance(raw, (list, tuple)) and kind == 'multi':
        parts = [str(part).strip() for part in raw if str(part).strip()]
        if not parts:
            return '', None
        return _multi(label, options, parts, ', '.join(parts))
    value = '' if raw is None else str(raw).strip()
    if value == '':
        return '', None
    if kind == 'yesno':
        if value.lower() in YES:
            return 'Yes', None
        if value.lower() in NO:
            return 'No', None
        return None, f'{label} takes Yes or No, not "{value}"'
    if kind == 'choice':
        match = match_option(value, options)
        if match is None:
            return None, f'{label} takes one of: {", ".join(map(str, options))} — "{value}" is not one of them'
        return match, None
    if kind == 'multi':
        return _multi(label, options, [part for part in MULTI_SPLIT.split(value) if part.strip()], value)
    if kind == 'date':
        parsed = parse_date(value)
        if parsed is None:
            return None, f'{label} takes a date, not "{value}"'
        return parsed.isoformat(), None
    if kind in ('number', 'money', 'percent'):
        number = value.replace(',', '').replace('$', '').replace('%', '').strip()
        if not NUMBER.match(number):
            return None, f'{label} takes a number, not "{value}"'
        return _plain_number(number), None
    if question['key'] == 'fein':
        digits = value.replace(' ', '')
        if not FEIN.match(digits):
            return None, f'FEIN takes XX-XXXXXXX, not "{value}"'
        digits = digits.replace('-', '')
        return f'{digits[:2]}-{digits[2:]}', None
    return value, None


def _multi(label, options, parts, value):
    picked, bad = [], []
    for part in parts:
        match = match_option(part, options)
        if match is None:
            bad.append(part.strip())
        elif match not in picked:
            picked.append(match)
    if bad or not picked:
        shown = ', '.join(map(str, options[:MULTI_SHOWN])) + ('…' if len(options) > MULTI_SHOWN else '')
        return None, f'{label} takes {shown}; not: {", ".join(bad) or value}'
    return picked, None


def _number(value):
    try:
        return Decimal(str(value).replace(',', '').replace('$', '').strip())
    except ArithmeticError:
        return None


def shown(question, answers):
    """Whether a question shows, from its `shown_when` rule over the stored answers (B2). A hidden question keeps its
    answer but never shows, counts or gets asked."""
    if isinstance(question, str):
        question = form.BY_KEY[question]
    rule = question.get('shown_when')
    if not rule:
        return True
    stored = answers.get(rule['field'])
    raw = '' if stored in (None, '') else (', '.join(stored) if isinstance(stored, list) else str(stored).strip())
    op = rule.get('op', 'nonempty')
    if op == 'nonempty':
        return raw != ''
    if op == 'eq':
        return raw == str(rule.get('value', ''))
    number, target = _number(raw) if raw else None, _number(rule.get('value'))
    if number is None or target is None or not number.is_finite():
        return False
    if op == 'gt':
        return number > target
    if op == 'gte':
        return number >= target
    return False


def hidden(answers):
    """The keys of the questions their rule hides, in form order."""
    return [question['key'] for question in form.QUESTIONS if not shown(question, answers)]
