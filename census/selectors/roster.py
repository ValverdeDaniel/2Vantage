"""One person as the roster grid draws them, and the roster-wide lists the grid asks for (plan.md §7.7; C3, C6, C8,
C24, OQ16, OQ28). Reads only.

- `person_row`: {id, kind, employee_id, values (SSNs masked), sources, issues, missing, review} — `review` names the
  cells with something to show (C3): `check` (⚑ flagged by a person), `to_check` (an open warning: a value Claude
  doubted, OQ28), `ignored` and `approved` (drawn only on a value that had a doubt, E92), sparse.
- `member_answer`: what a hand edit answers (C6): the changed person and their issues only, never the roster. Their
  issues are worked out over the whole census (a duplicate SSN needs everyone), and the stored summary rides along.
- `missing_refs`: every required blank on the roster, whatever page is shown (C24's "Select all missing").
"""

from deals import clock
from documents.review_rules import is_approved, is_ignored, mark_state, open_warning, shows_approval, warning_counts

from .. import facts, fields, validation
from ..values import mask_ssn

CHECKING = 'check'


def cell_review(entry):
    """'check' · 'to_check' · 'ignored' · 'approved' · '' for one source entry (the old `reviewMarkClass`)."""
    if mark_state(entry) == CHECKING:
        return 'check'
    if not shows_approval(entry):
        return ''
    if is_ignored(entry):
        return 'ignored'
    if is_approved(entry):
        return 'approved'
    return 'to_check' if open_warning(entry) else ''


def shown_values(values):
    """The person's values as a screen shows them: SSNs masked to their last four (OQ16)."""
    out = dict(values)
    for key in fields.SSN_KEYS:
        if out.get(key):
            out[key] = mask_ssn(out[key])
    return out


def issues_by_person(issues):
    """{person id: {key: [issue]}} from validation's {(id, key): [issue]}."""
    found = {}
    for (person_id, key), listed in issues.items():
        found.setdefault(person_id, {})[key] = listed
    return found


def person_row(person, issues, missing):
    """One person for the grid. `issues` = {key: [issue]}, `missing` = [keys]."""
    sources = person['sources'] or {}
    review = {key: state for key, entry in sources.items() if (state := cell_review(entry))}
    return {
        'id': person['id'],
        'kind': person['kind'],
        'employee_id': person['employee_id'],
        'values': shown_values(person['values']),
        'sources': sources,
        'issues': issues,
        'missing': missing,
        'review': review,
    }


def review_counts(found):
    """{open, check, unflagged} over every census cell (the roster's review bar, E48)."""
    return warning_counts(entry for person in found for entry in (person['sources'] or {}).values())


def member_answer(deal, member_id):
    """The PATCH answer's person (C6), with their issues and missing cells, and the stored summary."""
    found = facts.people(deal.id)
    person = next(p for p in found if p['id'] == member_id)
    needed = facts.needed(deal)
    issues = issues_by_person(validation.validate(found, clock.today())).get(member_id, {})
    return {
        'member': person_row(person, issues, facts.missing_keys(person, needed[person['kind']])),
        'summary': facts.summary(facts.stored(deal.id)),
        'review': review_counts(found),
    }


def missing_refs(deal):
    """["census:<id>:<key>"] for every required blank on the roster, in roster order (C24)."""
    found = sorted(facts.people(deal.id), key=lambda person: (person['position'], person['id']))
    needed = facts.needed(deal)
    return [
        f'census:{person["id"]}:{key}' for person in found for key in facts.missing_keys(person, needed[person['kind']])
    ]
