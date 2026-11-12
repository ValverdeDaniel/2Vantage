"""Mark as marketed (plan.md §5.2, §7.6; B33, B34, K33; OQ52).

`mark_marketed` stamps `Intake.marketed_at` and `marketed_by`. While the deal is not Ready to market it answers 409
listing the gaps (the questions, HR contact, Signed BOR, Census and the checklist's missing items); `override`
("Market anyway") confirms and records the skipped items in Activity — B34's fix: the old app recorded nothing. It
keeps the first `marketed_at`: a repeat changes nothing. A lost deal refuses it (`deals.rules.refuses(deal,
'send_to_market')`, §5.1). It moves no stage (OQ52 default): the deal reaches Quoting on the first quote read or RFP
send. Undo is Revert of its Activity row; `unmark_marketed` takes the stamp off by hand (§7.6 `unmark`).

Lock order: the Deal, then the Intake row. One Activity row (area `intake`, action `marketed`, never merged) under
`marketed:<deal id>` with `marketed_at` and `marketed_by` before and after, and — when the gate was skipped —
`skipped`: [None, every gap's words], which Revert leaves alone (it is a record, not a value). The summary names the
first six.
"""

from collections import namedtuple

from django.db import transaction
from django.utils.dateparse import parse_datetime

from deals import activity, clock, rules
from deals.services.snapshots import diff

from .. import selectors
from ..models import Intake
from . import rows

Marketed = namedtuple('Marketed', 'changed skipped activity')  # skipped: the gaps a Market anyway went past

ACTION = 'marketed'
SHOWN = 6  # the gaps a sentence names before "and N more"
FIELDS = ('marketed_at', 'marketed_by')


class NotReady(activity.Refused):
    """409: the deal is not Ready to market. Carries the gaps ({kind, key, label}) so the screen can list them and ask
    "Market anyway?"."""

    def __init__(self, gaps):
        super().__init__(f'This deal is not ready to market yet. Still open: {_named(gaps)}.', [g['key'] for g in gaps])
        self.detail = {'detail': self.sentence, 'keys': self.keys, 'gaps': gaps}


def target(deal_id):
    return f'marketed:{deal_id}'


def state(intake):
    return {
        'marketed_at': intake.marketed_at.isoformat() if intake.marketed_at else None,
        'marketed_by': intake.marketed_by_id,
    }


def _put(intake, values):
    at = values.get('marketed_at')
    intake.marketed_at = parse_datetime(at) if isinstance(at, str) else at
    intake.marketed_by_id = values.get('marketed_by')
    intake.save(update_fields=['marketed_at', 'marketed_by', 'updated_at'])


def _named(gaps):
    labels = [entry['label'] for entry in gaps]
    more = len(labels) - SHOWN
    return ', '.join(labels[:SHOWN]) + (f' and {more} more' if more > 0 else '')


def _summary(gaps):
    if not gaps:
        return 'Marked as marketed'
    return f'Marked as marketed anyway, skipping {len(gaps)}: {_named(gaps)}'


@transaction.atomic
def mark_marketed(user, deal_id, *, override=False):
    """Mark the deal as sent to market. Returns Marketed(changed, skipped gaps, Activity row or None). Raises NotReady
    (409 with the gaps) unless ready or `override`, and Refused on a lost deal."""
    deal = rows.lock_deal(deal_id)
    refusal = rules.refuses(deal, 'send_to_market')
    if refusal:
        raise activity.Refused(refusal)
    intake = rows.lock_intake(deal_id)
    if intake.marketed_at is not None:
        return Marketed({}, [], None)
    gaps = selectors.gate_of(deal)['ready']['gaps']
    if gaps and not override:
        raise NotReady(gaps)
    before = state(intake)
    _put(intake, {'marketed_at': clock.now(), 'marketed_by': user.id if user.is_authenticated else None})
    changed = diff(before, state(intake))
    recorded = {**changed, **({'skipped': [None, [entry['label'] for entry in gaps]]} if gaps else {})}
    row = activity.record(
        deal, user, rows.AREA, ACTION, _summary(gaps), changes=[activity.change(target(deal_id), recorded)]
    )
    return Marketed(changed, gaps, row)


@transaction.atomic
def unmark_marketed(user, deal_id):
    """Take "Sent to market" off. An unmarked deal changes nothing. Returns Marketed(changed, [], row or None)."""
    deal = rows.lock_deal(deal_id)
    if not Intake.objects.filter(deal_id=deal_id, marketed_at__isnull=False).exists():
        return Marketed({}, [], None)
    intake = rows.lock_intake(deal_id)
    before = state(intake)
    _put(intake, {'marketed_at': None, 'marketed_by': None})
    changed = diff(before, state(intake))
    row = activity.record(
        deal,
        user,
        rows.AREA,
        ACTION,
        'Took the deal off "Sent to market"',
        changes=[activity.change(target(deal_id), changed)],
    )
    return Marketed(changed, [], row)


def revert(deal_id, changed):
    """The stamp back to its "before" (intake/revert.py, after the Deal and Intake locks); `skipped` stays a record.
    Returns the diff it wrote."""
    intake = rows.lock_intake(deal_id)
    before = state(intake)
    wanted = {**before, **{key: pair[0] for key, pair in changed.items() if key in FIELDS}}
    if wanted == before:
        return {}
    _put(intake, wanted)
    return diff(before, state(intake))
