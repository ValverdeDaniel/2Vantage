"""The canary census of the staging canary scan (slice 47; plan.md §11.4 item 5, §12.9; Q.8; deploy/phi-gate.md).

Each run makes its own canaries: unique, synthetic strings for every PHI field a census carries (names, a spouse,
date of birth, SSN, address, city, phone, email), for the census file's name and for a stop-loss laser, so a later
log query finds this run's leaks and nobody else's. `forms(value)` is every spelling a log could hold it in: as
typed, URL-encoded and, for a date, as stored. Standard library only, like the rest of deploy/.
"""

import csv
import io
import json
import random
import string
from datetime import UTC, datetime
from urllib.parse import quote, quote_plus

HEADERS = ['First Name', 'Last Name', 'DOB', 'SSN', 'Gender', 'Address', 'City', 'State', 'Zip', 'Phone', 'Email',
           'Annual Salary', 'Relationship', 'Medical Tier']  # fmt: skip
FILLERS = 3  # synthetic people with no canary, so the census looks like one


def make(run=None):
    """{run, started_at, values: {field: value}}: one run's canaries."""
    rng = random.SystemRandom()
    run = run or ''.join(rng.choice(string.ascii_lowercase) for _ in range(6))
    year, month, day = rng.randint(1901, 1939), rng.randint(1, 12), rng.randint(1, 28)
    s_year, s_month = year + 2, month % 12 + 1
    ssn = f'{rng.randint(100, 665)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}'
    values = {
        'first_name': f'Zq{run}ia',
        'last_name': f'Vexcan{run}',
        'spouse_first_name': f'Zeph{run}ine',
        'dob': f'{month:02d}/{day:02d}/{year}',
        'dob_stored': f'{year}-{month:02d}-{day:02d}',
        'spouse_dob': f'{s_month:02d}/{day:02d}/{s_year}',
        'spouse_dob_stored': f'{s_year}-{s_month:02d}-{day:02d}',
        'ssn': ssn,
        'ssn_digits': ssn.replace('-', ''),
        'address': f'{rng.randint(100, 999)} Canary{run} Lane',
        'city': f'Canary{run}ville',
        'edited_city': f'Canary{run}town',
        'phone': f'555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}',
        'email': f'zq.{run}@canary.test',
        'laser': f'Claimant ZQL{run.upper()}: $250,000 (synthetic)',
    }
    return {'run': run, 'started_at': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'), 'values': values}


def file_name(canaries):
    """The census file's name carries the people's names, as real ones do (file names are PHI, §3.8)."""
    values = canaries['values']
    return f'{values["last_name"]} {values["first_name"]} census.csv'


def census_csv(canaries):
    values = canaries['values']
    employee = [values['first_name'], values['last_name'], values['dob'], values['ssn'], 'F', values['address'],
                values['city'], 'FL', '33101', values['phone'], values['email'], '91234', 'Employee', 'ES']  # fmt: skip
    spouse = [values['spouse_first_name'], values['last_name'], values['spouse_dob'], '', 'M', values['address'],
              values['city'], 'FL', '33101', '', '', '', 'Spouse', '']  # fmt: skip
    rows = [HEADERS, employee, spouse]
    for number in range(1, FILLERS + 1):
        rows.append([f'Filler{number}', 'Synthetic', f'0{number}/15/1980', '', 'M', f'{number} Synthetic Way',
                     'Orlando', 'FL', '32801', '', '', '50000', 'Employee', 'EE'])  # fmt: skip
    out = io.StringIO()
    csv.writer(out, lineterminator='\r\n').writerows(rows)
    return out.getvalue().encode('utf-8')


def forms(value):
    """Every spelling of `value` a log line could carry, lower-cased (the scan ignores case)."""
    found = {value, quote(value, safe=''), quote_plus(value), json.dumps(value)[1:-1]}
    return sorted({form.lower() for form in found if len(form) >= 6})


def searched(canaries):
    """{field: [spellings]} for the scan. The salary and the filler people are left out: too common to be a canary."""
    return {field: forms(value) for field, value in canaries['values'].items()}


def save(canaries, path):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(canaries, handle, indent=1)


def load(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)
