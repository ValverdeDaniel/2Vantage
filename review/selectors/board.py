"""The Review tab's Board (plan.md §7.13 `GET deals/{id}/review/board/`, §8.8; L1, L2, L7, L8, L9, L14, L28; O.6 #3).

{deal_id, asks_closed, counts {to_send, to_review, waiting, questions}, readiness {pct, state}, lanes {waiting
[request row], to_review [row]}, in_progress [{link_id, request_id, name, last_saved_at}], sections {intake, census}}.

- `counts` are the tab's own, from `rules.badges` over `summary.facts`, so the pills work before the shell's badges
  (slice 61) and agree with them after.
- `readiness` is the deal's intake readiness, the old board head's chip and bar (L2): the needed questions answered
  (`intake.summary.facts`) and the ready state (blocked, ready or submitted; words in /api/meta/ `review.readiness`).
- `lanes.waiting` holds the requests still out, soonest to run out first (L7); `lanes.to_review` (L9; slice 55) a row
  per section with something back: {key, section, count, questions, label, fix}, the census's answers and added
  people, the intake's answers, and the client's files; Review ▸ opens the section's queue. The Missing lane, Next and
  the client's questions join with slices 56–57.
- `sections` (slice 55): what each section bar draws (L14, C34), the section's `summary.facts` counts plus its
  `missing`: the intake's needed questions and checklist documents not in yet, the census's required blanks.
- `asks_closed` is the sentence when the deal may no longer ask its client (lost, archived, a past year): the tab then
  only reads (L129).
- `questions` (L5; slice 56): the client's open questions, oldest first, at most six, each {note_id, ref, section,
  where, who, at, excerpt (140 characters), fix}, and `questions_total`: Answer ▸ opens the request page on its tab.

A fixed number of queries however many requests, links and answers the deal has (Q.3 #4). Writes nothing.
"""

from deals import clock, rules
from intake import selectors as intake_selectors
from intake import summary as intake_summary
from intake.checklist import DOCUMENT

from .. import summary
from ..models import ReviewNote
from ..rules import badges
from ..rules import requests as request_rules
from . import items as item_rows
from . import notes as note_rows

QUESTIONS_SHOWN = 6
EXCERPT = 140
SECTIONS = {'intake': 'Intake', 'census': 'Census', 'documents': 'Documents'}


def _plural(n, one):
    return f'{n} {one}{"" if n == 1 else "s"}'


def _parts(questions, answers):
    """What a To review row holds, the question first (old `_parts`, D-159)."""
    found = ((questions, _plural(questions, 'question')), (answers, _plural(answers, 'answer')))
    return ' · '.join(words for n, words in found if n)


def _queue(section):
    return {'tab': 'review', 'view': 'queue', 'section': section}


def to_review(found):
    """The To review lane's rows (L9): each section with something back, its count holding its questions too."""
    census, intake = found['sections']['census'], found['sections']['intake']
    rows = [
        {
            'key': 'census',
            'section': 'Census',
            'count': census['to_review'] + census['questions'],
            'questions': census['questions'],
            'label': f'{_parts(census["questions"], census["to_review"])} from the client',
            'fix': _queue('census'),
        },
        {
            'key': 'intake',
            'section': 'Intake',
            'count': intake['to_review'] + intake['questions'],
            'questions': intake['questions'],
            'label': _parts(intake['questions'], intake['to_review']),
            'fix': _queue('intake'),
        },
        {
            'key': 'documents',
            'section': 'Documents',
            'count': (found.get('pending') or {}).get('documents', 0),
            'questions': 0,
            'label': 'files from the client to check',
            'fix': {'tab': 'documents'},
        },
    ]
    return [row for row in rows if row['count']]


def readiness(deal_id):
    """The intake readiness chip and bar from intake's facts (for a caller without the deal's intake payload)."""
    found = intake_summary.facts([deal_id]).get(deal_id) or {}
    needed, answered = found.get('needed', 0), found.get('answered', 0)
    return {'pct': round(answered / needed * 100) if needed else 100, 'state': found.get('ready_state') or 'blocked'}


def _intake(deal):
    """(readiness, missing) from intake's own payload: the needed questions answered and the ready state, and what
    the section bar counts as missing — the questions needed to market still blank (no client answer waiting) and the
    checklist's documents not in yet (old `missing + docs_missing`)."""
    payload = intake_selectors.intake_payload(deal)
    ready = payload.get('ready') or {}
    questions = sum(1 for gap in ready.get('gaps') or [] if gap.get('kind') == 'question')
    items = (payload.get('checklist') or {}).get('items') or []
    documents = sum(1 for item in items if item['satisfy'] == DOCUMENT and item['status'] == 'missing')
    return {'pct': payload['readiness']['pct'], 'state': ready.get('state') or 'blocked'}, questions + documents


def questions(deal):
    """([question row], total): the client's open questions, oldest first (old `_questions`, D-159)."""
    open_ = ReviewNote.objects.filter(deal_id=deal.id, kind='question', resolved_at__isnull=True)
    total = open_.count()
    rows = list(open_.select_related('link').order_by('at', 'id')[:QUESTIONS_SHOWN])
    found = item_rows.resolve(deal, [note_rows.ref_of(note) for note in rows])
    out = []
    for note in rows:
        ref = note_rows.ref_of(note)
        text = note.text.strip()
        item = found.get(ref)
        out.append(
            {
                'note_id': note.id,
                'ref': ref,
                'section': SECTIONS.get(note.surface, ''),
                'where': item.label if item else '',
                'who': note.link.name if note.link_id else '',
                'at': note.at.isoformat(),
                'excerpt': text if len(text) <= EXCERPT else f'{text[: EXCERPT - 1]}…',
                'fix': {'tab': 'review', 'view': 'request', 'pane': note.surface},
            }
        )
    return out, total


def board(deal, now=None):
    now = now or clock.now()
    facts, rows = summary.collect([deal.id], now)
    found = facts[deal.id]
    intake_readiness, missing = _intake(deal)
    sections = found['sections']
    sections['intake']['missing'] = missing
    waiting = [row for row in rows[deal.id] if row['state'] in request_rules.OPEN_STATES]
    asked, total = questions(deal)
    return {
        'deal_id': deal.id,
        'questions': asked,
        'questions_total': total,
        'asks_closed': rules.client_asks_open(deal),
        'counts': badges.counts(found),
        'readiness': intake_readiness,
        'lanes': {'waiting': request_rules.soonest_first(waiting), 'to_review': to_review(found)},
        'in_progress': found['in_progress'],
        'sections': sections,
    }
