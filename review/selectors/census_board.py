"""The Census board (plan.md §8.8, §8.10; C27, C28, C30, L46, L47; old 891f1b3 `CensusReviewView.jsx`,
`CensusReviewFieldRow.jsx`, `censusReviewRows.js`, `CensusRequestPanel.jsx`): one row per census COLUMN — the unit a
person decides about ("does this group have to give us hours?") — and a lens by person.

`board(deal, now)` → {columns: [column], people (the by-person lens, C30: `census_blanks.blanks`), employees,
dependents, file_hint (over 400 blanks: ask for their census file instead), asks_closed}. A column: {key, label,
group, help, rule (auto | required | waived), required, quoted, applies (employee | all), filled, total, counts
{missing, na, low, client, high} (the 5-segment bar, missing first), origins {origin: n} (where the filled values came
from), differs (the client sent something different), in_cart, asked, questions, askable}. Every number is the
server's (the old board's rule: the browser never counts a paged roster).
`drill(deal, column, now)` (C28: "▸ who (N)" / "▸ values (N)") → [{member_id, title, kind, value (words), origin,
theirs, differs, missing, asked, in_cart}] for one column. Staff only (names and values of people: `private,
no-store`); never SSN. The column assignee and partition mode are dropped (C29, L47, L67; OQ88's default).
"""

from collections import Counter

from census import client_view as census_view
from census import facts as census_facts
from census import fields
from census.models import CensusSettings, Member
from census.values import shown as shown_value
from deals import clock, rules
from documents import review_rules
from intake import client_entries

from .. import origins
from ..models import ReviewNote
from . import census_blanks, open_requests
from . import notes as note_rows
from .tray import out_with_client

FILE_HINT = 400  # blanks past which their census file is the better ask (C30)
SEGMENTS = ('missing', 'na', 'low', 'client', 'high')


def _facts(deal, now):
    questions = ReviewNote.objects.filter(deal_id=deal.id, kind='question', resolved_at__isnull=True)
    return {
        'drafts': {note_rows.ref_of(note) for note in note_rows.drafts(deal.id)},
        'out': set(out_with_client(deal, open_requests.load(deal.id), now)),
        'questions': {note_rows.ref_of(note) for note in questions.only('surface', 'key', 'member_id')},
    }


def _applies(key):
    group = fields.BY_KEY[key]['group']
    return 'employee' if group in fields.DEPENDENT_EXEMPT_GROUPS or key in fields.DEPENDENT_EXEMPT_KEYS else 'all'


def _cell(member, key, needed):
    """(segment, origin or '', differs) of one person's cell."""
    value = (member.values or {}).get(key)
    entry = (member.client or {}).get(key)
    if client_entries.pending(entry):
        theirs = entry.get('value')
        return 'client', 'waiting', bool(value) and theirs not in (None, '') and str(theirs) != str(value)
    if value in (None, ''):
        return ('missing' if key in needed.get(member.kind, ()) else 'na'), '', False
    source = (member.sources or {}).get(key) or {}
    origin = origins.origin_of(source)
    return ('low' if review_rules.open_warning(source) else 'high'), origin, False


def _column(key, people, needed, settings, quoted, facts):
    applies = _applies(key)
    counts, by_origin = Counter(), Counter()
    differs = in_cart = asked = questions = askable = 0
    for member in people:
        if applies == 'employee' and member.kind != fields.EMPLOYEE:
            continue
        segment, origin, different = _cell(member, key, needed)
        counts[segment] += 1
        if origin:
            by_origin[origin] += 1
        differs += different
        ref = f'census:{member.id}:{key}'
        in_cart += ref in facts['drafts']
        asked += ref in facts['out']
        questions += ref in facts['questions']
        askable += segment in ('missing', 'na') and ref not in facts['drafts'] and ref not in facts['out']
    total = sum(counts.values())
    return {
        'key': key,
        'label': fields.label(key),
        'group': fields.BY_KEY[key]['group'],
        'help': fields.BY_KEY[key].get('help', ''),
        'rule': settings.get(key, fields.AUTO),
        'required': any(key in keys for keys in needed.values()),
        'quoted': key in quoted,
        'applies': applies,
        'filled': counts['low'] + counts['high'],
        'total': total,
        'counts': {segment: counts[segment] for segment in SEGMENTS},
        'origins': dict(by_origin),
        'differs': differs,
        'in_cart': in_cart,
        'asked': asked,
        'questions': questions,
        'askable': askable,
    }


def board(deal, now=None):
    now = now or clock.now()
    needed = census_facts.needed(deal)
    settings = CensusSettings.objects.filter(deal_id=deal.id).values_list('rules', flat=True).first() or {}
    quoted = set(census_view.columns(deal, needed)[fields.EMPLOYEE])
    people = list(Member.objects.filter(deal_id=deal.id).only('id', 'kind', 'values', 'sources', 'client'))
    facts = _facts(deal, now)
    columns = [_column(key, people, needed, settings, quoted, facts) for key in fields.KEYS
               if key not in fields.SSN_KEYS]  # fmt: skip
    lens = census_blanks.blanks(deal)
    kinds = Counter(member.kind for member in people)
    return {
        'columns': columns,
        'people': lens,
        'employees': kinds[fields.EMPLOYEE],
        'dependents': kinds[fields.DEPENDENT],
        'file_hint': lens['total'] > FILE_HINT,
        'asks_closed': rules.client_asks_open(deal),
    }


def drill(deal, column, now=None):
    now = now or clock.now()
    needed = census_facts.needed(deal)
    facts = _facts(deal, now)
    applies = _applies(column)
    out = []
    for member in Member.objects.filter(deal_id=deal.id).order_by('position', 'id'):
        if applies == 'employee' and member.kind != fields.EMPLOYEE:
            continue
        segment, origin, different = _cell(member, column, needed)
        value = (member.values or {}).get(column)
        entry = (member.client or {}).get(column)
        theirs = entry.get('value') if client_entries.pending(entry) else None
        ref = f'census:{member.id}:{column}'
        out.append({
            'member_id': member.id,
            'ref': ref,
            'title': census_view.title(member),
            'kind': member.kind,
            'value': shown_value(column, value) if value else '',
            'origin': origin,
            'theirs': shown_value(column, theirs) if theirs not in (None, '') else '',
            'differs': different,
            'missing': segment == 'missing',
            'asked': ref in facts['out'],
            'in_cart': ref in facts['drafts'],
        })  # fmt: skip
    return out
