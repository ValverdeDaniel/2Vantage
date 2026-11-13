"""The request page's ask list, one tab at a time (plan.md §8.8; L28, L29; B12; old 891f1b3 `request_page.py`
`sections`, `RequestRail.jsx`): every item the client could be asked about on that tab, in the order they meet them,
each with where it stands (`rules.rail.status`).

`Facts` is what the page read once for the whole deal: the drafts by ref, what is out with the client ({ref: first
asked}), the client answers waiting (refs), the open questions and the notes by ref, the sent asks still open.
- `intake(deal, intake, facts)`: the questions the form shows, by section, then its parts (contacts, coverage in force,
  lines to quote, the BOR signature): {ref, label, section, needed, value, status, asked_at, draft_id, notes};
- `documents(deal, facts)`: the checklist's files (not waived): the same shape;
- `census(deal, facts)`: their census file as an item, and a row per census column {key, label, group, required,
  blank, required_blank, in_cart, asked, on_link, answered, questions}: a column's blanks are asked at once (L46).
A value rides as words, for staff only; never on a client's page.
"""

from collections import Counter, namedtuple

from census import client_view as census_view
from census import facts as census_facts
from census import fields as census_fields
from census.models import Member
from intake import form, values
from intake.checklist import DOCUMENT
from intake.selectors import gate_of

from ..rules import rail as rail_rules
from .queue_intake import shown as value_words

Facts = namedtuple('Facts', 'drafts out pending questions notes sent requests')

SECTION_LABELS = dict(form.SECTIONS)
BLOCKS = (
    ('contacts', 'Contacts'),
    ('coverage', 'Current coverage'),
    ('lines', 'Lines to quote'),
    ('bor', 'Broker of record signature'),
)
CENSUS_FILE = 'Their census file'


def _needed(key, rules):
    rule = values.rule_of(rules, key)
    return rule == values.REQUIRED if rule else form.BY_KEY[key]['need'] in ('Q', 'C')


def item(ref, label, section, facts, *, filled, needed=False, value=''):
    draft = facts.drafts.get(ref)
    return {
        'ref': ref,
        'label': label,
        'section': section,
        'needed': needed,
        'value': value,
        'status': rail_rules.status(
            question=ref in facts.questions,
            draft=draft is not None,
            pending=ref in facts.pending,
            asked=ref in facts.out,
            filled=filled,
        ),
        'asked_at': facts.out.get(ref),
        'draft_id': draft.id if draft is not None else None,
        'notes': facts.notes.get(ref, 0),
    }


def _block_filled(key, held, intake):
    if key == 'bor':
        return bool(intake and intake.bor_signed_at)
    return bool(held.get(f'block:{key}'))


def intake(deal, intake_row, facts):
    from intake import client_view

    held = client_view.stored(deal, intake_row)
    rules = (intake_row.rules if intake_row else None) or {}
    out = []
    for question in form.QUESTIONS:
        key = question['key']
        if not values.shown(question, held):
            continue
        value = held.get(key)
        filled = not values.blank(value)
        section = SECTION_LABELS.get(question['section'], '')
        words = value_words(key, value) if filled else ''
        out.append(item(f'intake:{key}', question['label'], section, facts, filled=filled,
                        needed=_needed(key, rules), value=words))  # fmt: skip
    for key, label in BLOCKS:
        filled = _block_filled(key, held, intake_row)
        out.append(item(f'intake:block:{key}', label, 'Contacts & coverage', facts, filled=filled))
    return out


def documents(deal, facts):
    rows = gate_of(deal)['checklist']['items']
    out = []
    for row in rows:
        if row.get('satisfy') != DOCUMENT or row['status'] == 'waived' or not row.get('kind'):
            continue
        out.append(item(f'doc:{row["kind"]}', row['label'], 'Marketing checklist', facts, filled=row['done'],
                        needed=row['status'] == 'missing'))  # fmt: skip
    return out


def _column_asked(column, requests):
    """Whether an open request's census scope asks this column now (not one value at a time)."""
    for asks in requests:
        census = asks.get('census') or {}
        scope = census.get('scope', 'none')
        if scope not in ('none', 'selected') and (not census.get('columns') or column in census['columns']):
            return True
    return False


def census(deal, facts):
    needed = census_facts.needed(deal)
    by_kind = census_view.columns(deal, needed)
    columns = by_kind[census_fields.EMPLOYEE]
    blank, required = Counter(), Counter()
    people = list(Member.objects.filter(deal_id=deal.id).only('id', 'kind', 'values'))
    for member in people:
        for key in by_kind.get(member.kind, columns):
            if (member.values or {}).get(key) in (None, ''):
                blank[key] += 1
                required[key] += key in needed.get(member.kind, ())
    by_column = {name: Counter() for name in ('in_cart', 'asked', 'answered', 'questions')}
    for ref in facts.drafts:
        _count(by_column['in_cart'], ref)
    for ref in facts.sent:
        _count(by_column['asked'], ref)
    for ref in facts.pending:
        _count(by_column['answered'], ref)
    for ref in facts.questions:
        _count(by_column['questions'], ref)
    rows = [
        {
            'key': key,
            'label': census_fields.label(key),
            'group': census_fields.BY_KEY[key]['group'],
            'required': any(key in keys for keys in needed.values()),
            'blank': blank[key],
            'required_blank': required[key],
            'on_link': _column_asked(key, facts.requests),
            **{name: counts[key] for name, counts in by_column.items()},
        }
        for key in columns
    ]
    return item('census:file', CENSUS_FILE, 'Census', facts, filled=bool(people)), rows


def _count(counter, ref):
    parts = ref.split(':')
    if len(parts) == 3 and parts[0] == 'census':
        counter[parts[2]] += 1
