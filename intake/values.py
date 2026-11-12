"""Intake answers: the one cleaner and the shown-when rule (plan.md §5.2; B2, B3, B.6). Pure.

`clean_value` is the one cleaner for the producer, Claude and portal paths (the old app had one for Claude only, so a
producer's typed answer was never checked; B.5). Ported from old Vantage 891f1b3 `market/intake_writes.py`
(`clean_value`, `_match_option`) and `market/intake.py` (`condition_met`), with §5.2's changes: a multi answer is a
list, a number is stored without trailing zeros, and dates are read without dateutil (the formats below).

`clean_answers` cleans a whole request with it, all or nothing (§7.6). `needed` is the one rule behind the rose star,
the "Missing" badge and readiness (B6, B33; old `needs`, D-064). Readiness's other parts (contacts, BOR, census, the
checklist and the ready state) are `intake/readiness.py` (slice 40).
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


REQUIRED, WAIVED = 'required', 'waived'
UNKNOWN = 'Not an intake question.'
NOT_TEXT = 'Send text, a number or (for a multi question) a list.'
GUIDANCE_LONG = f'Keep the client guidance under {form.GUIDANCE_LIMIT:,} characters.'


def rule_of(rules, key):
    """This deal's rule for a question (B37, OQ17): 'required', 'waived' or '' (Auto). Written by slice 57."""
    rule = (rules or {}).get(key)
    state = rule.get('state') if isinstance(rule, dict) else rule
    return state if state in (REQUIRED, WAIVED) else ''


def needed(question, answers, rules=None):
    """Whether the deal needs this question answered (B6, B33): never while hidden; Waived never, Required always;
    otherwise every quote-blocking (Q) question and every shown conditional (C) one."""
    if isinstance(question, str):
        question = form.BY_KEY[question]
    if not shown(question, answers):
        return False
    rule = rule_of(rules, question['key'])
    if rule:
        return rule == REQUIRED
    return question['need'] in ('Q', 'C')


def needed_keys(answers, rules=None):
    """The questions this deal needs, in form order."""
    return [question['key'] for question in form.QUESTIONS if needed(question, answers, rules)]


def blank(value):
    return value in (None, '', [])


def readiness(answers, needed_list):
    """The needed questions answered, and their share (§5.2: 100 when nothing is needed)."""
    answered = sum(1 for key in needed_list if not blank(answers.get(key)))
    pct = round(answered / len(needed_list) * 100) if needed_list else 100
    return {'needed': len(needed_list), 'answered': answered, 'pct': pct}


def _guidance(raw):
    text = '' if raw is None else str(raw).strip()
    return (None, GUIDANCE_LONG) if len(text) > form.GUIDANCE_LIMIT else (text, None)


def clean_answers(raw):
    """({key: cleaned value, '' to clear, or None to put back what was read}, {key: error}) for a request's answers.
    Every key is checked; the caller saves nothing when any fails (§7.6)."""
    cleaned, errors = {}, {}
    for key, value in raw.items():
        if key not in form.ANSWER_KEYS:
            errors[key] = UNKNOWN
            continue
        if value is None:
            cleaned[key] = None
            continue
        multi = key != form.GUIDANCE and form.BY_KEY[key]['type'] == 'multi'
        if isinstance(value, dict) or (isinstance(value, (list, tuple)) and not multi):
            errors[key] = NOT_TEXT
            continue
        result, error = _guidance(value) if key == form.GUIDANCE else clean_value(key, value)
        if error:
            errors[key] = error
        else:
            cleaned[key] = result
    return cleaned, errors
