"""A synthetic census roster for the census reader's tests (plan.md §12.1, Q.6, Q.8): a PDF made by code, Claude's
recorded answer for it, and the canary strings that must never leave the census (names, SSNs, birth dates)."""

import hashlib

import synthetic_files
from ai.services import start_read
from documents.tests.helpers import stored

CANARIES = (
    'Quillonbeck',
    'Zephyrine',
    'Marisolde',
    'Torvaldine',
    '539-26-8817',
    '539268817',
    '07/19/1983',
    '1983-07-19',
)

PAGE = [
    'Example Manufacturing (synthetic) - census',
    'Name  Rel  DOB  Gender  Zip  Medical tier',
    'Zephyrine Quillonbeck  EE  07/19/1983  F  33601  Family  SSN 539-26-8817',
    'Marisolde Quillonbeck  Spouse  02/02/1984  F',
    'Torvaldine Quillonbeck  Child  05/05/2015  M',
    'Oskar Pembleton  EE  03/03/1975  M  33602  Employee Only',
]


def roster_pdf():
    return synthetic_files.text_pdf(PAGE)


def value(key, text, page=1, unsure=False):
    return {'key': key, 'value': text, 'page': page, 'unsure': unsure}


ANSWER = {
    'people': [
        {
            'dependent': False,
            'employee': '',
            'values': [
                value('first_name', 'Zephyrine'),
                value('last_name', 'Quillonbeck'),
                value('dob', '07/19/1983'),
                value('gender', 'F'),
                value('zip', '33601'),
                value('medical_tier', 'Family'),
                value('ssn', '539-26-8817'),
            ],
        },
        {
            'dependent': True,
            'employee': 'Zephyrine Quillonbeck',
            'values': [
                value('first_name', 'Marisolde'),
                value('last_name', 'Quillonbeck'),
                value('relationship', 'Spouse'),
                value('dob', '02/02/1984', unsure=True),
                value('gender', 'F'),
            ],
        },
        {
            'dependent': True,
            'employee': 'Zephyrine Quillonbeck',
            'values': [
                value('first_name', 'Torvaldine'),
                value('last_name', 'Quillonbeck'),
                value('relationship', 'Child'),
                value('dob', '05/05/2015'),
                value('gender', 'M'),
            ],
        },
        {
            'dependent': False,
            'employee': '',
            'values': [
                value('first_name', 'Oskar'),
                value('last_name', 'Pembleton'),
                value('dob', '03/03/1975'),
                value('gender', 'M'),
                value('zip', '33602'),
                value('medical_tier', 'Employee Only'),
            ],
        },
    ]
}


def key(raw, label='p1'):
    return ('census', hashlib.sha256(raw).hexdigest()[:16], label)


def roster_read(user, deal, fake, answer=None):
    """Upload the roster PDF as a census file, record Claude's answer and read it; returns (job, document)."""
    raw = roster_pdf()
    document = stored(user, deal, 'roster (synthetic).pdf', raw, kind='census')
    fake.record(key(raw), answer or ANSWER)
    job, _ = start_read(user, deal, [document.id], target='census')
    job.refresh_from_db()
    return job, document


def leaks(text):
    """The canaries found in `text` (lower-cased match)."""
    low = str(text).lower()
    return [canary for canary in CANARIES if canary.lower() in low]
