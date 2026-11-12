"""Where a chat turn's changes go (plan.md §2, §10.1, §10.6; D71, D73, D76, D85, D86, D104; slice 24).

- `on_finish(job, change_set)` is the `turn` kind's land hook, in the transaction that ends the job: a direct
  person's (or an admin's) changes go on the table at once, with ↶ Undo this run, unless the table is locked from
  Claude (D104) or the deal is lost (O.3.7); everyone else's wait for review in the chat (`land.decide_turn`). A
  landing an owner refuses (the deal changed meanwhile) is taken back and the changes wait with its sentence.
- `land_turn(user, job, select)` lands the chosen items (all the ticked ones by default) through their owners
  (`registry.turn_owners`), in the chain's lock order after the Deal and the job, and returns what they wrote.
- `undo_turn(user, job, landed)` is ↶ Undo this run: every Activity row the landing wrote is reverted through its
  owner's reverter, newest first, all or nothing (a later change to a key refuses it with the owner's sentence).
- `retry_turn(user, job, ...)` is "Run anyway" on a turn the deal's budget stopped (D24) and ↻ Try again (D76): the
  same message answered again, on the next model when the person may use it.
"""

import logging

from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError

from deals import activity, clock, rules
from deals.activity import Refused

from .. import kinds, land, pricing, reading, registry
from ..models import DealAi, Job
from . import landing
from .jobs import NO_OPUS, NO_OVERRIDE, start

logger = logging.getLogger(__name__)

NOT_AN_ITEM = 'Pick changes this turn proposed.'
NOTHING_PICKED = 'Pick at least one change to apply.'
NO_OWNER = 'Changes of this kind cannot be applied here yet.'
STILL_GOING = 'This turn is still going: stop it first, or wait for it to finish.'
UNDO_FIRST = 'This turn changed the table: undo it first, then try again.'


def _chosen(items, select):
    if select is None:
        return [item for item in items if item.get('tick')]
    if not isinstance(select, list) or any(not isinstance(key, str) for key in select):
        raise ValidationError({'select': [NOT_AN_ITEM]})
    ids = {item['id'] for item in items}
    if any(key not in ids for key in select):
        raise ValidationError({'select': [NOT_AN_ITEM]})
    chosen = [item for item in items if item['id'] in set(select)]
    if not chosen:
        raise ValidationError({'select': [NOTHING_PICKED]})
    return chosen


def land_turn(user, job, select=None):
    """{activity_ids, activity_id, plan_ids, areas, summary, skipped}: the chosen items written through their owners,
    in the caller's transaction (the Deal and the job already locked)."""
    chosen = _chosen((job.result or {}).get('items') or [], select)
    by_owner = {}
    for item in chosen:
        by_owner.setdefault(item.get('owner'), []).append(item)
    if any(owner not in registry.turn_owners for owner in by_owner):
        raise Refused(NO_OWNER)
    landed = {'activity_ids': [], 'plan_ids': [], 'areas': [], 'summary': [], 'skipped': [], 'items': []}
    for owner in sorted(by_owner, key=lambda key: registry.turn_owners[key].order):
        wrote = registry.turn_owners[owner].apply(user, job.deal, job, by_owner[owner]) or {}
        landed['activity_ids'] += wrote.get('activity_ids') or []
        landed['plan_ids'] += [pid for pid in wrote.get('plan_ids') or [] if pid not in landed['plan_ids']]
        landed['areas'] += [area for area in wrote.get('areas') or [] if area not in landed['areas']]
        landed['skipped'] += wrote.get('skipped') or []
        if wrote.get('summary'):
            landed['summary'].append(wrote['summary'][:1].upper() + wrote['summary'][1:])
    landed['items'] = [item['id'] for item in chosen]
    landed['summary'] = ' · '.join(landed['summary']) or 'Nothing changed'
    landed['activity_id'] = landed['activity_ids'][-1] if landed['activity_ids'] else None
    return landed


def undo_turn(user, job, landed):
    """{reverted, at, by}: the landing's rows reverted, newest first; a refusal leaves everything as it was."""
    reverted = []
    with transaction.atomic():
        for row_id in sorted(landed.get('activity_ids') or [], reverse=True):
            reverted.append(activity.revert(row_id, user).id)
    return {'reverted': reverted, 'kept': [], 'skipped': [], 'at': clock.now().isoformat(), 'by': user.id}


def on_finish(job, change_set):
    """The job fields a finished turn ends with: landed ({land: auto, resolution: applied, result with `landed`}),
    waiting ({land: staged, wait_reason}), or nothing to land."""
    if not (change_set or {}).get('items'):
        return {}
    locked = landing._locked(job.id)
    user = locked.created_by
    decision = land.decide_turn(
        change_set,
        direct=landing.is_direct(user),
        locked=DealAi.objects.filter(deal_id=job.deal_id, locked_at__isnull=False).exists(),
        lost=rules.refuses(locked.deal, 'ai_land') or '',
    )
    if decision.mode != land.AUTO:
        return {'land': land.STAGED, 'wait_reason': decision.sentence[:200]}
    locked.result = change_set
    try:
        with transaction.atomic():  # a savepoint: a refused landing goes back alone, the turn still ends
            landed = land_turn(user, locked)
    except (Refused, APIException) as exc:
        return {'land': land.STAGED, 'wait_reason': landing._sentence(exc)}
    except Exception as exc:  # noqa: BLE001 - the changes wait; the class only, never its text (rule 10)
        logger.warning('Turn %s could not land by itself: %s', job.id, exc.__class__.__name__)
        return {'land': land.STAGED, 'wait_reason': landing.COULD_NOT}
    landed = {**landed, 'by': user.id, 'at': clock.now().isoformat(), 'auto': True}
    return {
        'land': land.AUTO,
        'wait_reason': '',
        'resolution': landing.APPLIED,
        'result': {**change_set, 'landed': landed},
        'activity_id': landed.get('activity_id'),
    }


def retry_turn(user, job, *, model='', budget_override=False):
    """(job, created): the same message answered again (Run anyway, Try again)."""
    if job.status in kinds.ACTIVE:
        raise Refused(STILL_GOING)
    if job.resolution == landing.APPLIED:
        raise Refused(UNDO_FIRST)
    if model and (model not in pricing.READ_MODELS or (model == pricing.OPUS and not reading.may_use_opus(user))):
        raise Refused(NO_OPUS)
    if budget_override and not reading.may_use_opus(user):
        raise Refused(NO_OVERRIDE)
    params = {key: value for key, value in (job.params or {}).items() if key not in ('model', 'budget_override')}
    if model:
        params['model'] = model
    if budget_override:
        params['budget_override'] = True
    params['retry_of'] = job.id
    started, created = start(user, job.deal, kinds.TURN, documents=job.documents, params=params, chat=job.chat)
    from ..models import ChatMessage

    ChatMessage.objects.filter(pk=params.get('message_id'), job=job).update(job=started)
    return Job.objects.get(pk=started.pk), created
