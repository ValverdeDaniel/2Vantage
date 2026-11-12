"""The issued versions, read (plan.md §7.12; J103, J.6.5): the packet card's Issued list, in the builder payload's
`issues` and `GET deals/{id}/proposal/issues/`. Reads only, in a fixed number of queries.

A version's state is worked out on read from its row and its job (rule 2): a version still `building` whose job has
ended without storing its files (the worker died and the reaper ended it, or it never got a job) reads `failed`, with
a sentence, so Retry is offered; the row itself is moved only by `finish`.

issue = {version, state: building | issued | failed, error, created_at, created_by, issued_at, issued_by,
         job: {id, status, progress, step} | null (while building), files: [{key, label, document_id, name, size}]}
"""

from ai import kinds
from deals.selectors import person

from ..models import ProposalIssue
from .catalog import FILE_KEYS, LABELS

STALLED = 'This stopped before the files were stored. Retry to build them.'


def state_of(row):
    if row.state != ProposalIssue.BUILDING:
        return row.state
    job = row.job
    if job is None or job.status not in kinds.ACTIVE:
        return ProposalIssue.FAILED
    return ProposalIssue.BUILDING


def building(deal):
    """The version still building on `deal` with its job going, or None."""
    rows = ProposalIssue.objects.filter(deal=deal, state=ProposalIssue.BUILDING).select_related('job')
    return next((row for row in rows if state_of(row) == ProposalIssue.BUILDING), None)


def _file(key, document):
    return {
        'key': key,
        'label': LABELS[key],
        'document_id': document.id,
        'name': document.original_name,
        'size': document.size,
    }


def payload(row):
    state = state_of(row)
    job = row.job
    error = row.error or ((job.error if job else '') or STALLED) if state == ProposalIssue.FAILED else ''
    return {
        'version': row.version,
        'state': state,
        'error': error,
        'created_at': row.created_at,
        'created_by': person(row.created_by),
        'issued_at': row.issued_at,
        'issued_by': person(row.issued_by),
        'job': (
            {'id': job.id, 'status': job.status, 'progress': job.progress, 'step': job.steps[-1] if job.steps else ''}
            if state == ProposalIssue.BUILDING
            else None
        ),
        'files': [_file(key, getattr(row, key)) for key in FILE_KEYS if getattr(row, f'{key}_id')],
    }


def issues(deal):
    """[issue], newest first."""
    rows = ProposalIssue.objects.filter(deal=deal).select_related('job', 'created_by', 'issued_by', *FILE_KEYS)
    return [payload(row) for row in rows]


def issued(deal, version):
    """The issued version `version` of `deal`, with its files, or None."""
    return (
        ProposalIssue.objects.filter(deal=deal, version=version, state=ProposalIssue.ISSUED)
        .select_related('deal__client', *FILE_KEYS)
        .first()
    )
