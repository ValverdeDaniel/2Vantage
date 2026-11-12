"""The intake's inline checks (plan.md §5.2 Validation; B8). Pure: answers and rows in, issues out.

`validate_intake(answers, coverage=…, contacts=…, today=…)` returns {key: [issue]}, issue = {code, severity,
message}, severity `error` or `warning`; a key is a question's key, `contact:<id>` or `coverage:<id>`. Issues are
advisory: they show beside the question and never block saving or "Ready to market" (OQ50 default). Ported from old
Vantage 891f1b3 `benefits/market/validation.py` (`validate_intake`), with §5.2's words and one new check,
`funding_contradiction`. The Form 5500 threshold is §5.2's 100 (the old app read it from a reminder rule).

The answers are the stored ones, already cleaned (`values.clean_value`), so the format checks (FEIN, state codes)
catch only a value that reached the row another way; the cleaner refuses a bad one at the door.
"""

import re
from decimal import Decimal, InvalidOperation

from deals import lines

ERROR, WARNING = 'error', 'warning'
FEIN = re.compile(r'\d{2}-?\d{7}')
STATE = re.compile(r'[A-Za-z]{2}')
EMAIL = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
FORM_5500_AT = 100
HOURS = (1, 40)
CHILD_AGE = (18, 30)
# The medical row's funding against "Are you self-funded?": the answer each funding contradicts.
CONTRADICTS = {'fully_insured': 'Yes', 'level_funded': 'No', 'self_funded': 'No'}
FUNDING_WORDS = {key: label.lower() for key, label in lines.FUNDING}


def issue(code, severity, message):
    return {'code': code, 'severity': severity, 'message': message}


def _text(answers, key):
    value = answers.get(key)
    if isinstance(value, list):
        return ' '.join(str(part) for part in value)
    return '' if value is None else str(value).strip()


def _number(answers, key):
    raw = _text(answers, key).replace(',', '').replace('$', '')
    if not raw:
        return None
    try:
        number = Decimal(raw)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _shown(number):
    """A count as the message prints it: '64', not '64.0'."""
    return format(number.to_integral_value(), 'f') if number == number.to_integral_value() else format(number, 'f')


def _a_year_after(day):
    try:
        return day.replace(year=day.year + 1)
    except ValueError:  # 29 February
        return day.replace(year=day.year + 1, day=28)


def _counts(answers, add):
    total, eligible = _number(answers, 'total_employees'), _number(answers, 'employee_count')
    enrolled, waiving = _number(answers, 'enrolled_count'), _number(answers, 'waiving_count')
    if total is not None and eligible is not None and eligible > total:
        message = f'Eligible employees ({_shown(eligible)}) exceeds total employees ({_shown(total)})'
        add('employee_count', issue('counts_order', ERROR, message))
    if eligible is not None and (enrolled is not None or waiving is not None):
        if (enrolled or 0) + (waiving or 0) > eligible:
            message = 'Enrolled + waiving is more than the eligible count — check the numbers'
            add('enrolled_count', issue('counts_sum', WARNING, message))
    if total is not None and total >= 50 and not _text(answers, 'ale_status'):
        message = f'{_shown(total)} employees — likely an ACA Applicable Large Employer; please confirm'
        add('ale_status', issue('ale_suggest', WARNING, message))


def _formats(answers, add):
    fein = _text(answers, 'fein')
    if fein and not FEIN.fullmatch(fein):
        add('fein', issue('fein_format', ERROR, f'FEIN "{fein}" is not in XX-XXXXXXX format'))
    situs = _text(answers, 'situs_state')
    if situs and not STATE.fullmatch(situs):
        add('situs_state', issue('state_format', WARNING, f'"{situs}" is not a 2-letter state code'))
    stored = answers.get('states_operating')
    codes = stored if isinstance(stored, list) else _text(answers, 'states_operating').replace(',', ' ').split()
    bad = next((str(code) for code in codes if not STATE.fullmatch(str(code).strip())), None)
    if bad is not None:
        add('states_operating', issue('state_format', WARNING, f'"{bad}" is not a 2-letter state code'))


def _compliance(answers, add, medical_funding):
    counts = [n for n in (_number(answers, 'enrolled_count'), _number(answers, 'enrolled_life_count')) if n is not None]
    peak = max(counts) if counts else None
    if peak is not None and peak >= FORM_5500_AT and _text(answers, 'form_5500_required') == 'No':
        message = (
            f'{_shown(peak)} enrolled on at least one benefit line but Form 5500 is marked "No" — did you make a '
            f'mistake, or is the group out of compliance? ({FORM_5500_AT}+ participants triggers a filing)'
        )
        add('form_5500_required', issue('form_5500_contradiction', ERROR, message))
    self_funded = _text(answers, 'self_funded')
    if self_funded == 'Yes' and _text(answers, 'pcori_filing') == 'No':
        message = 'Self-funded groups owe a PCORI filing (IRS Form 720, due July 31) — please double-check this answer'
        add('pcori_filing', issue('pcori_contradiction', WARNING, message))
    if self_funded and CONTRADICTS.get(medical_funding) == self_funded:
        words = FUNDING_WORDS.get(medical_funding, medical_funding)
        message = f'The medical coverage is recorded as {words} — check "Are you self-funded?"'
        add('self_funded', issue('funding_contradiction', WARNING, message))


def _ranges(answers, add):
    hours = _number(answers, 'hours_threshold')
    if hours is not None and not HOURS[0] <= hours <= HOURS[1]:
        add('hours_threshold', issue('hours_range', WARNING, 'Hours/week is usually between 1 and 40'))
    age = _number(answers, 'child_age_limit')
    if age is not None and not CHILD_AGE[0] <= age <= CHILD_AGE[1]:
        message = 'Dependent child age limit is usually 26 (allowed 18–30)'
        add('child_age_limit', issue('child_age_range', WARNING, message))


def validate_intake(answers, *, coverage=(), contacts=(), medical_funding='', today):
    """{key: [issue]} for the stored answers, the contacts ({id, email}) and the coverage rows ({id, renewal_date}).
    `medical_funding` is the medical line's funding as the deal records it (its current plans', else its row's)."""
    issues = {}

    def add(key, found):
        issues.setdefault(key, []).append(found)

    _formats(answers, add)
    _counts(answers, add)
    _compliance(answers, add, medical_funding)
    _ranges(answers, add)
    for contact in contacts:
        email = str(contact.get('email') or '').strip()
        if email and not EMAIL.fullmatch(email):
            add(f'contact:{contact["id"]}', issue('email_format', ERROR, f'"{email}" is not a valid email address'))
    for row in coverage:
        renewal = row.get('renewal_date')
        if renewal is None:
            continue
        if renewal < today:
            add(f'coverage:{row["id"]}', issue('renewal_past', WARNING, 'Renewal date is in the past'))
        elif renewal > _a_year_after(today):
            add(f'coverage:{row["id"]}', issue('renewal_far', WARNING, 'Renewal date is more than 12 months out'))
    return issues
