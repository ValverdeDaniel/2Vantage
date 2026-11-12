"""Starting and stopping jobs (plan.md §7.5, §10.2; D.6, O.3.3). The worker runs them; the web process never does.

- `start` queues a job in its kind's lane. The same job already queued or running (same kind, files and settings)
  is returned instead of a second one, so a double click starts one check. With AI_JOBS_INLINE (tests, plan §3.5) the
  job runs at once, in this process.
- `start_locate` is "Check this file" (E59): the deal's own files only.
- `cancel` is Stop: a queued job ends at once; a running one ends at its next beat, keeping what it finished. Stop on
  a stopped job changes nothing; on a finished one it is refused with a sentence.
A job is the AI's own working record, not deal data: starting or stopping one records no Activity. What a job changes
on the deal is recorded by the job (one row, `Job.activity`).
"""

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import clock
from deals.activity import Refused
from deals.models import Deal
from documents.models import Document

from .. import kinds, running
from ..models import Job

FINISHED = 'This has already finished, so there is nothing to stop.'
NO_FILES = 'Choose the files to check.'
NO_FILES_TO_READ = 'Choose the files to read.'
NOT_THIS_DEAL = 'Those files are not on this deal.'
NO_READER = 'Nothing reads files for that yet.'
NOT_READ_HERE = 'Claude reads {kinds} here; {count} of these files {verb} filed as something else.'
NO_OVERRIDE = 'Only an admin or a direct person can run a read past its cost cap.'
NO_OPUS = 'Opus 5.5 is kept to admins and direct people.'
WAITING = 'Waiting to start'
STOPPED_EARLY = 'Stopped before it started.'


def start(user, deal, kind, *, documents=(), params=None, target=''):
    """(job, created). `documents` are ids, kept in order."""
    lane = kinds.LANE_OF[kind]
    documents, params = list(documents), dict(params or {})
    with transaction.atomic():
        Deal.objects.select_for_update().only('id').get(pk=deal.id)  # two clicks at once start one job
        same = Job.objects.filter(
            deal=deal, kind=kind, target=target, status__in=kinds.ACTIVE, documents=documents, params=params
        ).first()
        if same is not None:
            return same, False
        job = Job.objects.create(
            deal=deal,
            lane=lane,
            kind=kind,
            target=target,
            documents=documents,
            params=params,
            created_by=user if getattr(user, 'is_authenticated', False) else None,
            steps=[WAITING],
        )
    if getattr(settings, 'AI_JOBS_INLINE', False):
        running.run_inline(job)
        job.refresh_from_db()
    return job, True


def start_locate(user, deal, document_ids, recheck=False):
    """Check these files' values against the files (E59). Every id must be a file of this deal (removed files too:
    their values still open them)."""
    if not document_ids:
        raise ValidationError({'document_ids': [NO_FILES]})
    ids = list(dict.fromkeys(document_ids))
    found = set(Document.all_objects.filter(deal=deal, pk__in=ids).values_list('id', flat=True))
    if found != set(ids):
        raise ValidationError({'document_ids': [NOT_THIS_DEAL]})
    return start(user, deal, kinds.LOCATE, documents=ids, params={'recheck': bool(recheck)})


def cancel(user, job_id):
    """(job, changed)."""
    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=job_id)
        if job.status == kinds.CANCELLED or (job.status in kinds.ACTIVE and job.cancel_requested_at):
            return job, False
        if job.status in kinds.FINISHED:
            raise Refused(FINISHED)
        now = clock.now()
        job.cancel_requested_at = now
        fields = ['cancel_requested_at', 'updated_at']
        if job.status == kinds.QUEUED:
            job.status, job.resolution, job.finished_at = kinds.CANCELLED, kinds.STOPPED, now
            job.steps = [*job.steps, STOPPED_EARLY][-kinds.STEPS_KEPT :]
            fields += ['status', 'resolution', 'finished_at', 'steps']
        job.save(update_fields=fields)
    return job, True


def start_read(
    user,
    deal,
    document_ids,
    *,
    target='quotes',
    pages=None,
    model='',
    budget_override=False,
    review=False,
    retry_of=None,
):
    """A read of these files by `target`'s reader (the one read door, D39; D46, D48). Refused with a sentence when
    Claude is not set up (409), the files are not this deal's or not of a kind the reader reads (400), or the person
    may not pick Opus or run past the cap (403-style sentences, 409). `review`: the read waits for review whoever
    starts it (the Re-read panel, E75); `retry_of`: the read it tries again (D76)."""
    from .. import client, pricing, reading, registry

    if not client.available():
        raise Refused(client.NoKey.sentence)
    reader = registry.readers.get(target)
    if reader is None:
        raise ValidationError({'target': [NO_READER]})
    if not document_ids:
        raise ValidationError({'document_ids': [NO_FILES_TO_READ]})
    ids = list(dict.fromkeys(document_ids))
    found = {doc.id: doc for doc in Document.objects.filter(deal=deal, pk__in=ids)}
    if set(found) != set(ids):
        raise ValidationError({'document_ids': [NOT_THIS_DEAL]})
    others = [doc for doc in found.values() if doc.kind not in reader.kinds]
    if others:
        kinds_said = ', '.join(reader.labels.get(kind, kind) for kind in reader.kinds)
        verb = 'is' if len(others) == 1 else 'are'
        raise ValidationError({'document_ids': [NOT_READ_HERE.format(kinds=kinds_said, count=len(others), verb=verb)]})
    if model and (model not in pricing.READ_MODELS or (model == pricing.OPUS and not reading.may_use_opus(user))):
        raise Refused(NO_OPUS)
    if budget_override and not reading.may_use_opus(user):
        raise Refused(NO_OVERRIDE)
    ordered = sorted(found.values(), key=lambda doc: (doc.uploaded_at, doc.id))  # upload order (D.6)
    params = {'model': model} if model else {}
    if pages:
        params['pages'] = sorted(set(pages))
    if budget_override:
        params['budget_override'] = True
    if review:
        params['review'] = True
    if retry_of:
        params['retry_of'] = int(retry_of)
    return start(user, deal, kinds.READ, documents=[doc.id for doc in ordered], params=params, target=target)
