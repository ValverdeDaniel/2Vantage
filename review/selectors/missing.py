"""The Board's Missing lane (plan.md §8.8; L6, L46, L48; old 891f1b3 `review/board.py` `_missing`, `_no_census_row`):
what the deal still needs from the client and nobody has.

One rule for every owner (L6 Ch. 2): a slot is missing when its stored value is blank and no client answer waits on
it. Asked items still count (they are still missing), and each row says how many have a client question open.
`lane(deal, payload, now, scope=None)` → [row], each {key, section, count, label, questions_open, items [words],
fix, ask, left}:
- `census`: the required census values still blank, by column ("Date of birth (3)"); its "＋ Ask all" asks those
  columns' required blanks (`{census: {columns, scope: missing}}`, the tray's door);
- `intake`: the questions required to market still blank (`{refs}`);
- `documents`: the checklist's files not on file (`{refs}`);
- `questionnaire:<form>` (slice 58, G76): each form the deal uses and nobody signed, its required answers blank on
  screen (a client's waiting answer or the live prefill fills a slot), named; its "＋ Ask them to fill it out
  online" (`ask_label`) puts the whole form in the tray (`qform:<form>`) until a request asks it whole;
- on the census's own board (`scope` census) with nobody on the roster, "No census on file yet", which asks for
  their census file.
`left` is what "＋ Ask all" would still add: not in the tray and not out with the client; `ask` is None once nothing
is left (the button hides). `payload` is the intake's own (`intake.selectors.intake_payload`), which the Board reads
anyway. Staff only; a fixed number of queries.
"""

from collections import Counter

from census import facts as census_facts
from census import fields as census_fields
from census.models import Member
from intake import client_entries
from intake.checklist import DOCUMENT
from intake.models import Intake

from ..models import ReviewNote
from ..rules import policy
from ..rules.requests import carries
from . import notes as note_rows
from . import open_requests

GAP = 'question'  # intake.readiness.QUESTION: a needed question still blank
ONLINE = '＋ Ask them to fill it out online'


def _plural(n, one):
    return f'{n} {one}{"" if n == 1 else "s"}'


def _with_questions(words, asked):
    return f'{words} ({asked} with a question open)' if asked else words


def _census(deal, drafted, requests, asked):
    """(row or None, blank refs) over the people: required cells blank with no client answer waiting."""
    needed = census_facts.needed(deal)
    by_column, refs = Counter(), []
    people = list(Member.objects.filter(deal_id=deal.id).only('id', 'kind', 'values', 'client'))
    for member in people:
        client = member.client or {}
        for key in needed.get(member.kind, ()):
            if (member.values or {}).get(key) in (None, '') and not client_entries.pending(client.get(key)):
                by_column[key] += 1
                refs.append(f'census:{member.id}:{key}')
    if not refs:
        return None, people
    columns = [key for key, _n in sorted(by_column.items(), key=lambda pair: (-pair[1], census_fields.label(pair[0])))]
    taken = _asked(refs, drafted, requests)
    left = [ref for ref in refs if ref not in taken]
    questions = sum(1 for ref in refs if ref in asked)
    return {
        'key': 'census',
        'section': 'Census',
        'count': len(refs),
        'label': _with_questions(f'{_plural(len(refs), "required census value")} still blank', questions),
        'questions_open': questions,
        'items': [f'{census_fields.label(key)} ({by_column[key]})' for key in columns],
        'fix': {'tab': 'review', 'view': 'board', 'section': 'census', 'lane': 'missing'},
        'ask': {'census': {'columns': columns, 'scope': 'missing'}} if left else None,
        'left': len(left),
    }, people


def _row(key, section, words, rows, taken, asked, fix):
    refs = [ref for ref, _label in rows]
    left = [ref for ref in refs if ref not in taken]
    questions = sum(1 for ref in refs if ref in asked)
    return {
        'key': key,
        'section': section,
        'count': len(rows),
        'label': _with_questions(words, questions),
        'questions_open': questions,
        'items': [label for _ref, label in rows],
        'fix': fix,
        'ask': {'refs': left} if left else None,
        'left': len(left),
    }


def _intake(deal, payload):
    """([(ref, label)] required to market and blank with no client answer waiting, [(ref, label)] files missing)."""
    client = Intake.objects.filter(deal_id=deal.id).values_list('client', flat=True).first() or {}
    gaps = (payload.get('ready') or {}).get('gaps') or []
    questions = [
        (f'intake:{gap["key"]}', gap['label'])
        for gap in gaps
        if gap['kind'] == GAP and not client_entries.pending(client.get(gap['key']))
    ]
    items = (payload.get('checklist') or {}).get('items') or []
    files = [
        (f'doc:{item["kind"]}', item['label'])
        for item in items
        if item.get('satisfy') == DOCUMENT and item['status'] == 'missing' and item.get('kind')
    ]
    return questions, files


def _taken(deal, now):
    """(drafts and open sent asks, [the asks of each open request a person was sent]): what "＋ Ask all" leaves be.
    A fixed number of queries: whether a request asks a missing slot is `carries` over the lane's own refs."""
    taken = {note_rows.ref_of(note) for note in note_rows.drafts(deal.id)}
    found = open_requests.load(deal.id)
    opens = open_requests.opens(found, now)
    taken |= {note_rows.ref_of(note) for note in note_rows.sent_asks([deal.id]).get(deal.id, [])
              if opens.get(note.request_id)}  # fmt: skip
    out = []
    for request, links in found.values():
        closed = request.closed_at is not None
        if any(link.sent_at and policy.opens(link, now, closed=closed) for link in links):
            out.append(request.asks or {})
    return taken, out


def _asked(refs, taken, requests):
    """The refs in the tray or out with the client: a missing slot is blank and needed, so a scope asks it."""
    every = frozenset(refs)
    return {ref for ref in refs if ref in taken or any(carries(asks, ref, missing=every, blank=every)
                                                        for asks in requests)}  # fmt: skip


def form_blanks(deal):
    """[(form, [(slot, label)])] for each form the deal uses that nobody signed, its required answers still blank."""
    from questionnaire import forms
    from questionnaire.engine import walk
    from questionnaire.selectors import context

    from .queue_questionnaire import label

    ctx = context.deal_context(deal)
    armed = [found['form'] for found in ctx.resolved.values() if found['form']]
    if not armed:
        return []
    facts = context.prefill_facts(deal)
    out = []
    for key in [key for key in forms.FORMS if key in armed]:
        row = ctx.stored.get(key)
        if row is not None and row.locked:
            continue
        view = context.form_view(key, row, facts)
        numbers = {(b, e['id']): at + 1 for b, listed in view.stored.rows.items() for at, e in enumerate(listed)}
        blanks = walk.blanks(view.form, view.view)
        if blanks:
            out.append((key, [(slot, label(view.form, slot, numbers)[0]) for slot in blanks]))
    return out


def _forms(deal, drafted, requests, asked):
    from questionnaire import forms

    rows = []
    for key, blanks in form_blanks(deal):
        refs = [f'q:{key}:{slot}' for slot, _label in blanks]
        whole = f'qform:{key}'
        taken = _asked([whole, *refs], drafted, requests)
        out_already = whole in taken or all(ref in taken for ref in refs)
        questions = sum(1 for ref in refs if ref in asked)
        words = f'{_plural(len(blanks), "required answer")} on {forms.label(key)} still blank'
        rows.append({
            'key': f'questionnaire:{key}', 'section': 'Questionnaire', 'count': len(blanks),
            'label': _with_questions(words, questions), 'questions_open': questions,
            'items': [words_ for _slot, words_ in blanks], 'fix': {'tab': 'questionnaire', 'form': key},
            'ask': None if out_already else {'refs': [whole]}, 'ask_label': ONLINE, 'left': 0 if out_already else 1,
        })  # fmt: skip
    return rows


def lane(deal, payload, now, *, scope=None):
    drafted, requests = _taken(deal, now)
    open_questions = ReviewNote.objects.filter(deal_id=deal.id, kind='question', resolved_at__isnull=True)
    asked = {note_rows.ref_of(note) for note in open_questions.only('surface', 'key', 'member_id')}
    rows = []
    if scope in (None, 'census'):
        census, people = _census(deal, drafted, requests, asked)
        if scope == 'census' and not people:
            file_asked = bool(_asked(['census:file'], drafted, requests))
            rows.append({
                'key': 'census_file', 'section': 'Census', 'count': 1, 'label': 'No census on file yet',
                'questions_open': 0, 'items': [], 'fix': {'tab': 'census'},
                'ask': None if file_asked else {'refs': ['census:file']}, 'left': 0 if file_asked else 1,
            })  # fmt: skip
        if census:
            rows.append(census)
    if scope in (None, 'intake'):
        questions, files = _intake(deal, payload)
        fix = {'tab': 'review', 'view': 'board', 'section': 'intake', 'lane': 'missing'}
        if questions:
            verb = 'is' if len(questions) == 1 else 'are'
            words = f'{_plural(len(questions), "question")} required to market {verb} unanswered'
            taken = _asked([ref for ref, _label in questions], drafted, requests)
            rows.append(_row('intake', 'Intake', words, questions, taken, asked, fix))
        if files:
            words = f'{_plural(len(files), "document")} not on file yet'
            taken = _asked([ref for ref, _label in files], drafted, requests)
            rows.append(_row('documents', 'Documents', words, files, taken, asked, fix))
    if scope in (None, 'questionnaire'):
        rows += _forms(deal, drafted, requests, asked)
    return rows
