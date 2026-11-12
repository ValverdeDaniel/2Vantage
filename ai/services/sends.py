"""Attaching files to Claude, and trying a read again (plan.md §8.17, §10.4, §10.5; D16, D17, D23, D24, D76; slice 20).

- `start_send` is what attaching does in Work with Claude: attaching is the request (D17). The files just attached are
  read by the reader of their kind, one read per reader, started in `kinds.SEND_ORDER` (the census, the
  questionnaire and intake first, the plans last), so the worker runs them in that order, one after another on the
  deal (a drop is never refused: the send queues, D16). Files no reader reads stay filed, and say so.
- `retry` is ↻ Try again (D76, D23): the same files read again, by the next model up the ladder when the person may
  use it (Sonnet 5.5 → Opus 5.5, D91), else by the same one. A read that landed is undone first (409 with
  `can_force` when something changed since, as ↶ Undo this run; `force` is "Undo anyway"); one waiting for review is
  discarded; a failed, stopped or over-budget one just reads again. The new read names the old (`params.retry_of`).
  Run anyway (D24) is the same door with `budget_override`.
"""

from django.conf import settings
from rest_framework.exceptions import ValidationError

from deals.activity import Refused
from documents.models import Document

from .. import client, kinds, pricing, registry
from ..models import Job
from . import landing
from .jobs import NO_FILES_TO_READ, NO_OPUS, NO_OVERRIDE, NOT_THIS_DEAL, start_read

NOT_A_READ = 'Only a read can be tried again.'
STILL_GOING = 'This read is still going: stop it first, or wait for it to finish.'


def target_of(kind):
    """The reader that reads files of `kind` in a send, or None."""
    for target in kinds.SEND_ORDER:
        reader = registry.readers.get(target)
        if reader is not None and kind in reader.kinds:
            return target
    return None


def start_send(user, deal, document_ids, *, model='', budget_override=False):
    """([(job, created)] in the order they run, [ids of the files no reader reads])."""
    if not client.available():
        raise Refused(client.NoKey.sentence)
    if not document_ids:
        raise ValidationError({'document_ids': [NO_FILES_TO_READ]})
    ids = list(dict.fromkeys(document_ids))
    found = {doc.id: doc for doc in Document.objects.filter(deal=deal, pk__in=ids)}
    if set(found) != set(ids):
        raise ValidationError({'document_ids': [NOT_THIS_DEAL]})
    groups, not_read = {}, []
    for doc in sorted(found.values(), key=lambda doc: (doc.uploaded_at, doc.id)):
        target = target_of(doc.kind)
        if target is None:
            not_read.append(doc.id)
        else:
            groups.setdefault(target, []).append(doc.id)
    jobs = [
        start_read(user, deal, groups[target], target=target, model=model, budget_override=budget_override)
        for target in kinds.SEND_ORDER
        if target in groups
    ]
    return jobs, not_read


def model_of(job):
    asked = job.model or (job.params or {}).get('model') or settings.AI_MODEL
    return asked if asked in pricing.READ_MODELS else settings.AI_MODEL


def next_model(job, user):
    """The model "Try again" reads with: the next up the ladder when the person may use it, else the same."""
    from ..reading import may_use_opus

    ladder = list(pricing.READ_MODELS)
    now = model_of(job)
    later = ladder[ladder.index(now) + 1 :] if now in ladder else []
    allowed = [model for model in later if model != pricing.OPUS or may_use_opus(user)]
    return allowed[0] if allowed else now


def retry(user, job_id, *, model='', force=False, budget_override=False):
    """(job, created): the new read."""
    from ..reading import may_use_opus

    job = Job.objects.select_related('deal').get(pk=job_id)
    if job.kind == kinds.TURN:  # Run anyway on a turn the budget stopped, ↻ Try again on a turn (slice 24)
        from .turns import retry_turn

        return retry_turn(user, job, model=model, budget_override=budget_override)
    if job.kind != kinds.READ:
        raise Refused(NOT_A_READ)
    if job.status in kinds.ACTIVE:
        raise Refused(STILL_GOING)
    model = model or next_model(job, user)
    if model not in pricing.READ_MODELS or (model == pricing.OPUS and not may_use_opus(user)):
        raise Refused(NO_OPUS)
    params = job.params or {}
    budget_override = budget_override or bool(params.get('budget_override'))
    if budget_override and not may_use_opus(user):
        raise Refused(NO_OVERRIDE)
    if job.resolution == landing.APPLIED:
        landing.undo(user, job.id, force=force)
    elif landing.waiting(job):
        landing.discard(user, job.id)
    return start_read(
        user,
        job.deal,
        job.documents,
        target=job.target,
        pages=params.get('pages'),
        model=model,
        budget_override=budget_override,
        review=bool(params.get('review')),
        retry_of=job.id,
        plan=params.get('plan'),
    )
