"""Census validation (plan.md §5.3.4; C21). Pure; computed on read, over the whole census (duplicates need it).

Ported from old Vantage 891f1b3 `market/validation.py` (`validate_case`), with one severity word, `error` or `warning`
(the old `warn` hid the duplicate-person warning, C3), ages in whole years, and §5.3.4's messages. A person:
{id, kind, employee_id, values}. Missing required cells are not issues here: `facts` and the page count them apart.
"""

import re

from . import fields
from .importer.words import CHILD_WORDS, SPOUSE_WORDS, is_waiver, tier_code
from .values import age_on, digits, parse_date

ERROR, WARNING = 'error', 'warning'
MISSING = {'code': 'missing_required', 'severity': ERROR, 'message': 'Required'}
DUPLICATE_SSN = 'Duplicate SSN — another person in this census has the same SSN'
SAME_PERSON = 'The same person twice? Another row has this name and date of birth'
_ZIP = re.compile(r'\d{5}(-\d{4})?')
_STATE = re.compile(r'[A-Za-z]{2}')


def issue(code, severity, message):
    return {'code': code, 'severity': severity, 'message': message}


def _ssn(person, add, seen):
    ssn = (person['values'].get('ssn') or '').strip()
    if not ssn:
        return
    found = digits(ssn)
    if len(found) != 9:
        add('ssn', issue('ssn_format', ERROR, f'SSN "{ssn}" is not 9 digits'))
    elif found.startswith(('000', '666', '9')):
        add('ssn', issue('ssn_invalid', ERROR, f'SSN "{ssn}" is not a valid SSN range'))
    elif found in seen:
        add('ssn', issue('ssn_duplicate', ERROR, DUPLICATE_SSN))
        seen[found](issue('ssn_duplicate', ERROR, DUPLICATE_SSN))
    else:
        seen[found] = lambda found_issue: add('ssn', found_issue)


def _dob(person, add, today):
    raw = (person['values'].get('dob') or '').strip()
    if not raw:
        return
    born = parse_date(raw)
    if born is None:
        add('dob', issue('dob_unparseable', ERROR, f'Could not read "{raw}" as a date'))
        return
    age = age_on(born, today)
    if born > today:
        add('dob', issue('dob_future', ERROR, 'Date of birth is in the future'))
    elif age > 110:
        add('dob', issue('dob_age', ERROR, f'Age {age} — check the birth year'))
    elif person['kind'] == fields.EMPLOYEE and age < 14:
        add('dob', issue('dob_young', WARNING, f'Employee is {age} years old — check the date of birth'))


def _address(values, add):
    zip_code = (values.get('zip') or '').strip()
    if zip_code and not _ZIP.fullmatch(zip_code):
        add('zip', issue('zip_format', WARNING, f'ZIP "{zip_code}" is not a 5-digit ZIP'))
    state = (values.get('state') or '').strip()
    if state and not _STATE.fullmatch(state):
        add('state', issue('state_format', WARNING, f'State "{state}" is not a 2-letter code'))


def _tiers(values, add):
    for key in fields.TIER_KEYS:
        raw = (values.get(key) or '').strip()
        if raw and not tier_code(raw) and not is_waiver(raw):
            message = f'{fields.label(key)} "{raw}" is not one of EE / ES / EC / FAM / Waived'
            add(key, issue('tier_unknown', ERROR, message))


def _employee(person, dependents, add):
    values = person['values']
    tier = tier_code(values.get('medical_tier'))
    relationships = [(dep['values'].get('relationship') or '').strip().lower() for dep in dependents]
    spouse = any(any(word in rel for word in SPOUSE_WORDS) for rel in relationships)
    child = any(any(word in rel for word in CHILD_WORDS) for rel in relationships)
    if tier == 'EE' and dependents:
        add('medical_tier', issue('tier_ee_deps', WARNING, 'Tier is Employee Only but dependents are listed'))
    elif tier == 'EC' and not child:
        add(
            'medical_tier',
            issue('tier_ec_no_child', WARNING, 'Tier is EE + Child(ren) but no child dependent is listed'),
        )
    elif tier == 'ES' and not spouse:
        add(
            'medical_tier', issue('tier_es_no_spouse', WARNING, 'Tier is EE + Spouse but no spouse dependent is listed')
        )
    elif tier == 'FAM' and not dependents:
        add('medical_tier', issue('tier_fam_no_deps', WARNING, 'Tier is Family but no dependents are listed'))
    hired, effective = parse_date(values.get('hire_date')), parse_date(values.get('effective_date'))
    if hired and effective and hired > effective:
        add('hire_date', issue('hire_after_effective', WARNING, 'Hire date is after the coverage effective date'))


def validate(people, today):
    """{(person id, key): [issue]} for every cell with an issue, over the whole census as of `today`."""
    issues = {}
    by_employee = {}
    for person in people:
        if person['kind'] == fields.DEPENDENT and person.get('employee_id'):
            by_employee.setdefault(person['employee_id'], []).append(person)
    ssn_seen, person_seen = {}, {}
    for person in people:

        def add(key, found, person_id=person['id']):
            issues.setdefault((person_id, key), []).append(found)

        values = person['values']
        _ssn(person, add, ssn_seen)
        who = tuple((values.get(key) or '').strip().lower() for key in ('last_name', 'first_name', 'dob'))
        if all(who):
            if who in person_seen:
                add('last_name', issue('person_duplicate', WARNING, SAME_PERSON))
                person_seen[who]('last_name', issue('person_duplicate', WARNING, SAME_PERSON))
            else:
                person_seen[who] = add
        _dob(person, add, today)
        _address(values, add)
        _tiers(values, add)
        if person['kind'] == fields.DEPENDENT:
            if not (values.get('relationship') or '').strip():
                add('relationship', issue('dep_relationship', ERROR, 'Dependent is missing a relationship'))
            if not person.get('employee_id'):
                add('relationship', issue('dep_orphan', ERROR, 'Dependent is not linked to an employee'))
            continue
        _employee(person, by_employee.get(person['id'], []), add)
    return issues


def counts(issues):
    """(errors, warnings) over every issue."""
    found = [item['severity'] for listed in issues.values() for item in listed]
    return found.count(ERROR), found.count(WARNING)
