"""Synthetic census people for the RFP's file tests: made by code, never a real file (plan.md §12.1, Q.8)."""

import io

from census import services as census_services

EMPLOYEE, DEPENDENT = 'employee', 'dependent'


def person(pid, kind=EMPLOYEE, employee_id=None, **values):
    """A person as `census.facts.people` answers them."""
    return {
        'id': pid,
        'kind': kind,
        'employee_id': employee_id,
        'position': pid,
        'values': {key: value for key, value in values.items() if value not in ('', None)},
        'sources': {},
        'client': {},
    }


def employee(pid, **values):
    base = {
        'first_name': f'Avery{pid}',
        'last_name': 'Synthetic',
        'dob': '1980-01-15',
        'gender': 'F',
        'zip': '33101',
        'hours_per_week': '40',
        'medical_tier': 'EE',
        'medical_plan': 'Gold PPO',
        'dental_tier': 'EE',
        'vision_tier': 'EE',
    }
    return person(pid, EMPLOYEE, None, **{**base, **values})


def dependent(pid, employee_id, **values):
    base = {
        'first_name': f'Kid{pid}',
        'last_name': 'Synthetic',
        'dob': '2012-06-01',
        'gender': 'M',
        'relationship': 'Child',
    }
    return person(pid, DEPENDENT, employee_id, **{**base, **values})


def crowd(n):
    """n employees, no dependents (for the caps)."""
    return [employee(i + 1) for i in range(n)]


def add(user, deal, people):
    """Put synthetic people on a deal through census's own door; returns the members in order."""
    made, ids = [], {}
    for found in people:
        employee_id = ids.get(found['employee_id']) if found['kind'] == DEPENDENT else None
        member, _row = census_services.add_member(
            user, deal.id, found['kind'], employee_id=employee_id, values=dict(found['values'])
        )
        ids[found['id']] = member.id
        made.append(member)
    return made


def family(user, deal):
    """One employee with a spouse and a child, and a second employee alone (the smallest roster with a family)."""
    return add(
        user,
        deal,
        [
            employee(1, first_name='Avery', employment_status='Full-time', annual_salary='61500', emp_class='Salaried'),
            dependent(2, 1, first_name='Blair', relationship='Spouse', dob='1981-03-02', gender='F'),
            dependent(3, 1, first_name='Casey', relationship='Son'),
            employee(4, first_name='Devon', zip='07030', medical_tier='ES', employment_status='COBRA'),
        ],
    )


def book(content):
    import openpyxl

    return openpyxl.load_workbook(io.BytesIO(content))
