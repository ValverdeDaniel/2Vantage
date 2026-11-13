"""`GET deals/{id}/journey/`: the deal shell's one read (plan.md §7.15, §8.4; A21, A23, A24, M39, M40, I68, I120;
slice 61). Reads only, in a fixed number of queries whatever the deal holds: the facts once (`facts.facts_for`, every
app's stored counts and EXISTS checks inside one batch scope), the marks, then pure rules.

{deal_id, today, next_step, waiting, journey: {modules, complete}, progress, badges, meters, ready}

- `journey`: the stepper (A24, M39): Get to Market and Quote to Close, each milestone `done`, `current` or `todo`
  with the tab its dot opens. The current dot is the milestone that owns the deal's next step (`catalogue.
  milestone_of`), so dot and banner agree; a step no milestone owns leaves it on the first milestone still to do. No
  step is ever "skipped" (M40): a milestone a quote-first deal went past reads to do, and never counts (`progress`).
- `badges`: the sidebar's counts as the old workspace drew them (A21, L13, H9; old CaseWorkspace `badges`): Review's
  three tones and "?" (`review.rules.badges`, the tab's own counts), Intake (needed questions still blank and checklist
  documents not in), Census (errors and warnings), Proposal (required values blank and open warnings on the proposed
  plans), Commission's 1 while no primary producer is set; `returned` (the violet ↩: client answers or questions
  waiting on that section) and `asked` (its open client questions).
- `meters`: Deal readiness, Intake, Proposal and Census (A23; Hand-off dropped).
- `ready`: intake's ready state, the sidebar chip (B33; words in /api/meta/ `review.readiness`).
"""

from deals import clock
from intake.checklist import DOCUMENT
from review.rules import badges as review_badges

from . import catalogue, journey, marks, rows, selectors
from .facts import facts_for
from .steps import steps

SECTIONS = ('intake', 'census', 'questionnaire')


def stepper(milestones, next_step):
    """{modules: [{key, label, pct, steps: [{key, label, tab, state}]}], complete} from `journey.journey`."""
    owner = catalogue.milestone_of((next_step or {}).get('key'))
    done = {row['key'] for row in milestones if row['state'] == journey.DONE}
    if (next_step or {}).get('state') == 'lost':
        current = None
    elif owner and owner not in done:
        current = owner
    else:
        current = next((row['key'] for row in milestones if row['current']), None)
    modules = []
    for group, label in catalogue.GROUP_LABELS.items():
        mine = [row for row in milestones if row['group'] == group]
        counted = [row for row in mine if row['state'] != journey.SKIPPED]
        finished = sum(1 for row in counted if row['state'] == journey.DONE)
        steps = []
        for row in mine:
            state = 'done' if row['state'] == journey.DONE else 'current' if row['key'] == current else 'todo'
            steps.append({'key': row['key'], 'label': row['label'], 'tab': catalogue.MILESTONE_TABS[row['key']],
                          'state': state})  # fmt: skip
        pct = round(finished / len(counted) * 100) if counted else 100
        modules.append({'key': group, 'label': label, 'pct': pct, 'steps': steps})
    progress = journey.progress(milestones)
    return {'modules': modules, 'complete': progress['total'] > 0 and progress['done'] == progress['total']}


def _intake_missing(intake):
    """Needed questions still blank and checklist documents not in (the board's Missing; old `missing +
    docs_missing`)."""
    questions = sum(1 for gap in intake.get('blockers') or [] if gap.get('kind') == 'question')
    documents = sum(
        1 for item in intake.get('items') or [] if item.get('satisfy') == DOCUMENT and item.get('status') == 'missing'
    )
    return questions + documents


def badges(facts):
    intake, census, quotes = facts.get('intake') or {}, facts.get('census') or {}, facts.get('quotes') or {}
    review = facts.get('review') or {}
    sections = review.get('sections') or {}
    counts = review_badges.counts(review)
    intake_missing = _intake_missing(intake)
    census_missing = (sections.get('census') or {}).get('missing', 0)

    def section(name, key):
        return (sections.get(name) or {}).get(key, 0) or 0

    return {
        'review': {
            'review': counts['to_review'],
            'waiting': counts['waiting'],
            'missing': intake_missing + census_missing,
            'questions': counts['questions'],
        },
        'intake': intake_missing,
        'census': (census.get('errors') or 0) + (census.get('warnings') or 0),
        'proposal': (quotes.get('required_missing') or 0) + (quotes.get('to_review') or 0),
        'commission': 1 if (facts.get('commission') or {}).get('needs_primary') else 0,
        'returned': {name: section(name, 'to_review') + section(name, 'questions') > 0 for name in SECTIONS},
        'asked': {name: section(name, 'questions') for name in SECTIONS},
    }


def meters(facts):
    """Deal readiness (A23): Intake (needed questions answered), Proposal (required values filled on the proposed
    plans; old `proposal_metrics`) and Census (`census.facts.readiness`)."""
    quotes = facts.get('quotes') or {}
    total = quotes.get('required_total') or 0
    proposal = round((quotes.get('required_filled') or 0) / total * 100) if total else 100
    return {
        'intake': (facts.get('intake') or {}).get('readiness_pct', 100),
        'proposal': proposal,
        'census': (facts.get('census') or {}).get('readiness_pct', 100),
    }


def journey_read(deal):
    """The payload above. A lost deal keeps its meters and badges (its facts are read), and has no steps (I66)."""
    now, today = clock.now(), clock.today()
    facts = facts_for([deal.id], now, lost_too=True)[deal.id]
    unmarked = steps(facts, today, now)
    marked = marks.apply_marks(unmarked, selectors.stored_marks(deal.id), today)
    next_step = selectors.next_of(deal.id, facts, marked)
    milestones = journey.journey(facts, unmarked)
    return {
        'deal_id': deal.id,
        'today': today.isoformat(),
        'next_step': next_step,
        'waiting': None if facts['deal']['lost'] else rows.waiting(marked, today),
        'journey': stepper(milestones, next_step),
        'progress': journey.progress(milestones),
        'badges': badges(facts),
        'meters': meters(facts),
        'ready': (facts.get('intake') or {}).get('ready_state'),
    }
