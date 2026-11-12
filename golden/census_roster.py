"""GD4's people, made by code from the spec's census groups (plan.md §13.4; slice 12). Synthetic only.

Each group is `n` employees with one medical plan text and tier; an ES employee has a spouse, EC one child (`children`
says more), FAM a spouse and two children. Dental and vision follow the medical tier unless the group names theirs,
with the spec's dental and vision plan texts when enrolled. A group may also give: `aged_65` (the birth dates of its
first employees, aged 65 or more at the effective date), `spouse_dobs` (its spouses' birth dates, '' for the made
one), `hours` ({hours: how many of its last employees work them}; else 40), `waiver_reason`, and `canary` (its first
employee and spouse carry the spec's PHI canaries, Q.8). Everything else is made from the employee's number, so the
same spec always makes the same people, and the key counts them by hand from the groups. The census's `id_prefix`
(default "G4") starts each employee id ("G3-001" on GD3, slice 13).
"""

import datetime

PREFIXES = [
    'Ash', 'Birch', 'Cedar', 'Dale', 'Elm', 'Fern', 'Glen', 'Hazel', 'Iris', 'Juniper', 'Kestrel', 'Larch', 'Maple',
    'North', 'Oak', 'Pine', 'Quarry', 'Rowan', 'Sedge', 'Thorn',
]  # fmt: skip
SUFFIXES = ['field', 'wood', 'brook', 'ridge', 'ford']
FIRSTS = [
    'Avery', 'Blair', 'Casey', 'Devon', 'Emerson', 'Finley', 'Gray', 'Harper', 'Indy', 'Jordan', 'Kendall', 'Logan',
    'Morgan', 'Noel', 'Oakley', 'Parker', 'Quinn', 'Reese', 'Sawyer', 'Taylor', 'Umber', 'Vale', 'Wren', 'Yael',
]  # fmt: skip
SPOUSES = ['Alex', 'Bailey', 'Cameron', 'Drew', 'Ellis', 'Frankie', 'Gale', 'Hollis', 'Jamie', 'Kai', 'Lane', 'Marlo']
CHILDREN = ['Arlo', 'Bea', 'Cole', 'Dot', 'Eli', 'Fay', 'Gus', 'Hope', 'Ivo', 'June', 'Kit', 'Lou', 'Mae', 'Ned']
CITIES = ['Orlando', 'Tampa', 'Ocala', 'Sarasota', 'Lakeland']
TITLES = ['Machinist', 'Assembler', 'Shift Lead', 'Planner', 'Accountant', 'Driver', 'Inspector', 'Buyer']
TIERS = ('EE', 'ES', 'EC', 'FAM')


def _date(year, month, day):
    return datetime.date(year, month, day).isoformat()


def _last_name(number):
    base = PREFIXES[(number - 1) // len(SUFFIXES) % len(PREFIXES)] + SUFFIXES[(number - 1) % len(SUFFIXES)]
    return base if number <= len(PREFIXES) * len(SUFFIXES) else f'{base}{number}'


def _employee(number, group, index, census):
    tier = group['tier']
    dental, vision = group.get('dental', tier), group.get('vision', tier)
    aged = group.get('aged_65') or []
    hours = 40
    left = group['n'] - index  # 1 for the group's last employee
    for worked, count in (group.get('hours') or {}).items():
        if left <= count:
            hours = int(worked)
    year = 1966 + (number * 7) % 30
    return {
        'kind': 'employee',
        'ext_emp_id': f'{census.get("id_prefix", "G4")}-{number:03d}',
        'relationship': 'Employee',
        'first_name': FIRSTS[(number - 1) % len(FIRSTS)],
        'last_name': _last_name(number),
        'dob': aged[index] if index < len(aged) else _date(year, number % 12 + 1, number % 27 + 1),
        'gender': 'F' if number % 2 else 'M',
        'address1': f'{100 + number} Synthetic Way',
        'city': CITIES[number % len(CITIES)],
        'state': 'FL',
        'zip': f'33{100 + number % 100:03d}',
        'phone': f'555-01{number % 100:02d}',
        'email': f'{census.get("id_prefix", "G4").lower()}.employee{number:03d}@example.test',
        'hire_date': _date(2010 + number % 15, 3, 1),
        'hours_per_week': hours,
        'annual_salary': 42000 + 750 * (number % 40),
        'job_title': TITLES[number % len(TITLES)],
        'medical_plan': group['medical_plan'],
        'medical_tier': tier,
        'effective_date': census['medical_effective'] if tier in TIERS else '',
        'waiver_reason': group.get('waiver_reason', ''),
        'dental_plan': census['dental_plan'] if dental in TIERS else '',
        'dental_tier': dental,
        'vision_plan': census['vision_plan'] if vision in TIERS else '',
        'vision_tier': vision,
    }


def _dependent(employee, relationship, first, dob, gender):
    keep = ('ext_emp_id', 'last_name', 'city', 'state', 'zip')
    return {
        'kind': 'dependent',
        **{key: employee[key] for key in keep},
        'relationship': relationship,
        'first_name': first,
        'dob': dob,
        'gender': gender,
    }


def _family(number, group, index, census, canaries):
    employee = _employee(number, group, index, census)
    spouse_first = SPOUSES[(number - 1) % len(SPOUSES)]
    if group.get('canary') and index == 0:
        employee.update(
            {key: canaries[key] for key in ('first_name', 'last_name', 'dob', 'address1', 'phone', 'email')}
        )
        spouse_first = canaries['spouse_first_name']
    people = [employee]
    tier, born = group['tier'], int(employee['dob'][:4])
    if tier in ('ES', 'FAM'):
        dobs = group.get('spouse_dobs') or []
        dob = dobs[index] if index < len(dobs) and dobs[index] else _date(born + 1, number % 12 + 1, 15)
        people.append(_dependent(employee, 'Spouse', spouse_first, dob, 'M' if employee['gender'] == 'F' else 'F'))
    children = 2 if tier == 'FAM' else group.get('children', 1) if tier == 'EC' else 0
    for k in range(children):
        first = CHILDREN[(number + k) % len(CHILDREN)]
        dob = _date(2008 + (number + k) % 12, (number + k) % 12 + 1, 10)
        people.append(_dependent(employee, 'Child', first, dob, 'F' if (number + k) % 2 else 'M'))
    return people


def people(spec):
    """Every person of the spec's census, each employee followed by their dependents."""
    census = spec['census']
    out, number = [], 0
    for group in census['groups']:
        for index in range(group['n']):
            number += 1
            out += _family(number, group, index, census, census.get('canaries') or {})
    return out
