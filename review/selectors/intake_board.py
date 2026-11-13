"""The Intake board (plan.md §8.8, §8.9; B37, L45, L48, L122; old 891f1b3 `IntakeReviewView.jsx`,
`intake_review.board`): a row per intake question — the answer and where it came from, whether THIS deal needs it
(Auto, Required or Waived: the one `values.needed` rule readiness, the `required` ask and the star read), the note the
client reads instead of our help text, which open requests already ask it, whether the client sent something
different — and the checklist's files not on file.

`board(deal, now)` → {rows: [row], documents: [doc], counts {gap, pending, answered, optional, waived, total},
asks_closed}. A row: {key, ref, label, section, section_label, help, seed (qb | cond | opt), rule ('' | required |
waived), note, needed, shown, value (words), filled, origin, status (gap | pending | answered | optional), differs,
theirs (their waiting answer, words), asked_in [names], asked_at, draft_id, question_open}. A document: {ref, label,
status, missing, asked_at, draft_id, question_open}. Staff only; a fixed number of queries. Writes nothing.
"""

from deals import clock, rules
from intake import client_entries, client_view, form, values
from intake.checklist import DOCUMENT
from intake.models import Intake
from intake.selectors import gate_of
from intake.services.rules import note_of

from .. import origins
from ..models import ReviewNote
from ..portal import asked as asked_rules
from ..rules import policy
from . import notes as note_rows
from . import open_requests
from .queue_intake import shown as value_words
from .tray import out_with_client

SECTION_LABELS = dict(form.SECTIONS)
SEEDS = {'Q': 'qb', 'C': 'cond'}


def _asked_in(deal, intake, found, now):
    """{ref: [names]}: the open, sent requests asking each intake ref now."""
    out = {}
    for request, links in found.values():
        closed = request.closed_at is not None
        live = [link for link in links if link.sent_at and policy.opens(link, now, closed=closed)]
        if not live:
            continue
        names = [link.name or 'Private link' for link in live]
        for ref in asked_rules.outline(request, deal, intake):
            out.setdefault(ref, [])
            out[ref] += [name for name in names if name not in out[ref]]
    return out


def _status(needed, filled, waiting, rule):
    if waiting:
        return 'pending'
    if filled:
        return 'answered'
    if rule == values.WAIVED:
        return 'waived'
    return 'gap' if needed else 'optional'


def _row(question, held, intake, facts):
    key = question['key']
    ref = f'intake:{key}'
    rules_ = (intake.rules if intake else None) or {}
    sources = (intake.sources if intake else None) or {}
    entry = ((intake.client if intake else None) or {}).get(key)
    waiting = client_entries.pending(entry)
    value = held.get(key)
    filled = not values.blank(value)
    rule = values.rule_of(rules_, key)
    needed = values.needed(question, held, rules_)
    theirs = entry.get('value') if waiting else None
    return {
        'key': key,
        'ref': ref,
        'label': question['label'],
        'section': question['section'],
        'section_label': SECTION_LABELS.get(question['section'], ''),
        'help': question.get('help', ''),
        'seed': SEEDS.get(question['need'], 'opt'),
        'rule': rule,
        'note': note_of(rules_.get(key)),
        'needed': needed,
        'shown': values.shown(question, held),
        'value': value_words(key, value) if filled else '',
        'filled': filled,
        'origin': origins.origin_of(sources.get(key)) if filled else '',
        'status': _status(needed, filled, waiting, rule),
        'differs': waiting and filled and not values.blank(theirs) and str(theirs) != str(value),
        'theirs': value_words(key, theirs) if waiting and not values.blank(theirs) else '',
        'asked_in': facts['asked_in'].get(ref, []),
        'asked_at': facts['out'].get(ref),
        'draft_id': facts['drafts'].get(ref),
        'question_open': ref in facts['questions'],
    }


def _documents(deal, facts):
    out = []
    for item in gate_of(deal)['checklist']['items']:
        if item.get('satisfy') != DOCUMENT or not item.get('kind') or item['status'] == 'waived':
            continue
        ref = f'doc:{item["kind"]}'
        out.append({
            'ref': ref,
            'label': item['label'],
            'status': item['status'],
            'missing': item['status'] == 'missing',
            'asked_at': facts['out'].get(ref),
            'draft_id': facts['drafts'].get(ref),
            'question_open': ref in facts['questions'],
        })  # fmt: skip
    return out


def board(deal, now=None):
    now = now or clock.now()
    intake = Intake.objects.filter(deal_id=deal.id).first()
    held = client_view.stored(deal, intake)
    found = open_requests.load(deal.id)
    questions = ReviewNote.objects.filter(deal_id=deal.id, kind='question', resolved_at__isnull=True)
    facts = {
        'asked_in': _asked_in(deal, intake, found, now),
        'out': out_with_client(deal, found, now),
        'drafts': {note_rows.ref_of(note): note.id for note in note_rows.drafts(deal.id)},
        'questions': {note_rows.ref_of(note) for note in questions.only('surface', 'key', 'member_id')},
    }
    rows = [_row(question, held, intake, facts) for question in form.QUESTIONS]
    counts = {status: 0 for status in ('gap', 'pending', 'answered', 'optional', 'waived')}
    for row in rows:
        if row['shown']:
            counts[row['status']] += 1
    counts['total'] = sum(counts.values())
    return {
        'rows': rows,
        'documents': _documents(deal, facts),
        'counts': counts,
        'asks_closed': rules.client_asks_open(deal),
    }
