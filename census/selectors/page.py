"""The census page (plan.md §7.7; C1, C2, C22, C24; OQ16). Reads only; writes nothing.

The summary and the rollup are the stored counts (`CensusFacts`); validation issues and missing cells are worked out
on read over the whole census (duplicates need it), and only one page of people is returned: employees, each followed
by their dependents, unlinked dependents on the last page. `show=issues` keeps families where someone has an issue,
`show=missing` those with a missing required cell; `q` matches a first or last name. SSNs are shown masked (OQ16).
The roster grid (slice 41) reads it: each person as `roster.person_row` draws them, the roster's review counts (E48)
and the COBRA tick, read through intake's door (`intake.selectors.checklist_item`; C25, O.6 #2).
"""

from math import ceil

from deals import clock
from intake.checklist import COBRA
from intake.models import Intake
from intake.selectors import checklist_item

from .. import facts, fields, rollup, validation
from ..models import CensusImport
from .imports import import_row
from .roster import issues_by_person, person_row, review_counts

PAGE_SIZE, MAX_PAGE_SIZE = 100, 500
SHOWS = ('all', 'issues', 'missing')
ALWAYS = ('identity', 'demographics', 'employment', 'medical')


def columns(deal, found):
    """The keys in scope for the deal (C2): the person and employment groups, medical, the groups of the lines to
    quote and any group that holds data."""
    requested = set(deal.requested_lines or [])
    groups = set(ALWAYS)
    groups |= {group for group, keys in fields.GROUP_LINES.items() if requested & set(keys)}
    held = {key for person in found for key in person['values']}
    groups |= {fields.BY_KEY[key]['group'] for key in held if key in fields.BY_KEY}
    return [field['key'] for field in fields.FIELDS if field['group'] in groups]


def line_rollups(deal, stored_rollup):
    """{line: rollup.for_line(...)} for medical and each line to quote the census holds figures for (§5.3.6)."""
    wanted = ['medical', *[line for line in deal.requested_lines or [] if line != 'medical']]
    found = {line: rollup.for_line(stored_rollup, line) for line in wanted}
    return {line: figures for line, figures in found.items() if figures}


def derived(deal, found):
    """FTE (C45) and the 65+ count (C46), worked out on read: they follow the intake's hours threshold and the
    deal's effective date."""
    answers = Intake.objects.filter(deal_id=deal.id).values_list('answers', flat=True).first() or {}
    threshold = str(answers.get('hours_threshold') or '').strip() or None
    return {
        'fte': rollup.fte(found, threshold),
        'aged_65': rollup.aged_65(found, deal.effective_date),
        'as_of': deal.effective_date.isoformat() if deal.effective_date else None,
        'hours_threshold': threshold or str(rollup.DEFAULT_FULL_TIME_HOURS),
    }


def family_groups(found):
    """[[employee, its dependents…]] in roster order, unlinked dependents last, each alone."""
    by_employee = {}
    for person in found:
        if person['kind'] == fields.DEPENDENT and person['employee_id']:
            by_employee.setdefault(person['employee_id'], []).append(person)
    families = [[person, *by_employee.get(person['id'], [])] for person in found if person['kind'] == fields.EMPLOYEE]
    known = {person['id'] for person in found if person['kind'] == fields.EMPLOYEE}
    orphans = [p for p in found if p['kind'] == fields.DEPENDENT and p['employee_id'] not in known]
    return families + [[person] for person in orphans]


def _keep(family, show, query, issues, missing):
    if query and not any(
        query in (person['values'].get(key) or '').lower() for person in family for key in ('first_name', 'last_name')
    ):
        return False
    if show == 'issues':
        return any(key[0] == person['id'] for person in family for key in issues)
    if show == 'missing':
        return any(missing.get(person['id']) for person in family)
    return True


def census_page(deal, page=1, page_size=PAGE_SIZE, show='all', query=''):
    """The census page (§7.7)."""
    found = sorted(facts.people(deal.id), key=lambda person: (person['position'], person['id']))
    stored = facts.stored(deal.id)
    issues = validation.validate(found, clock.today())
    needed = facts.needed(deal)
    missing = {person['id']: facts.missing_keys(person, needed[person['kind']]) for person in found}
    families = [f for f in family_groups(found) if _keep(f, show, query.strip().lower(), issues, missing)]
    pages = max(1, ceil(len(families) / page_size))
    number = min(max(1, page), pages)
    shown = [person for family in families[(number - 1) * page_size : number * page_size] for person in family]
    by_person = issues_by_person(issues)
    return {
        'summary': facts.summary(stored),
        'rollup': line_rollups(deal, stored['rollup']),
        'derived': derived(deal, found),
        'columns': columns(deal, found),
        'imports': [import_row(imp) for imp in CensusImport.objects.filter(deal=deal).select_related('document__deal')],
        'last_import_at': stored['last_import_at'].isoformat() if stored['last_import_at'] else None,
        'page': {'number': number, 'pages': pages, 'page_size': page_size, 'employees': len(families)},
        'members': [person_row(person, by_person.get(person['id'], {}), missing[person['id']]) for person in shown],
        'review': review_counts(found),
        'cobra': checklist_item(deal.id, COBRA),
    }
