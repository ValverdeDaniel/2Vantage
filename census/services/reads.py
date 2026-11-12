"""A Claude read of a census, staged as an import for the Census tab (plan.md §5.3.2, §10.4, §10.5; C11, C19, D29,
D74, D109, D110; slice 51).

- `stage_read(user, deal_id, job_id, document_id, merged)`: the people a PDF roster read found become a proposed import
  that points at its read; the roster is untouched. An earlier proposal waiting on the deal is set aside (one mapping
  to review on the tab), with its read.
- `stage_sheet(user, deal_id, job_id, document_id, opened, mapping, assisted)`: a census spreadsheet sent to Claude:
  the importer's import, its columns as the offline mapper proposed them with the mapping assist's proposals for the
  ones it left unmapped or doubted (shapes only, D109), pointing at its read.
- `reader_apply` / `reader_discard`: the read's own "Use this scan ▸" and Discard, through the import's apply and
  discard, so the job and its import always agree.
Activity says counts only, never a person or a value (§3.8): "Claude read a census file: 12 people (4 dependents)".
"""

from django.db import transaction

from deals import activity

from ..models import CensusImport
from ..reader import staged
from . import rows
from .apply import apply_import, landed
from .imports import discard_import

NOT_STAGED = 'This census read has no import waiting, so there is nothing to use.'
NO_UNDO = 'A census import is not undone here. Import the census file you want again: its dry run shows what moves.'


def _plural(count, one, many):
    return f'{count} {one if count == 1 else many}'


def _record(deal, user, imp, summary):
    return activity.record(deal, user, rows.AREA, 'proposed', summary, document_id=imp.document_id, actor_kind='claude')


@transaction.atomic
def stage_read(user, deal_id, job_id, document_id, merged):
    """The proposed import of a census read (merge.merge's people); returns it."""
    deal = rows.lock_deal(deal_id)
    rows.set_aside_waiting(deal_id, current_job=job_id)
    read = staged.stored(merged)
    imp = CensusImport.objects.create(
        deal=deal,
        document_id=document_id,
        job_id=job_id,
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        sheet_name='',
        header_row=1,
        first_data_row=2,
        headers=[column['header'] for column in staged.mapping(read['keys'])],
        mapping=staged.mapping(read['keys']),
        read=read,
    )
    counted = staged.counts(read)
    people = _plural(counted['people'], 'person', 'people')
    dependents = _plural(counted['dependents'], 'dependent', 'dependents')
    _record(deal, user, imp, f'Claude read a census file: {people} ({dependents})')
    return imp


@transaction.atomic
def stage_sheet(user, deal_id, job_id, document_id, opened, mapping, assisted):
    """The proposed import of a census spreadsheet Claude was given; returns it."""
    deal = rows.lock_deal(deal_id)
    rows.set_aside_waiting(deal_id, current_job=job_id)
    imp = CensusImport.objects.create(
        deal=deal,
        document_id=document_id,
        job_id=job_id,
        created_by=user if getattr(user, 'is_authenticated', False) else None,
        sheet_name=opened.sheet[:100],
        header_row=opened.header_row,
        first_data_row=opened.first_data_row,
        headers=opened.table.headers,
        pivot=opened.recipe,
        mapping=mapping,
    )
    mapped = sum(1 for item in mapping if item['field'])
    summary = f'Mapped a census file: {mapped} of {len(mapping)} columns'
    if assisted:
        summary += f', {assisted} proposed by Claude from the column shapes'
    _record(deal, user, imp, summary)
    return imp


def waiting_import(job):
    return CensusImport.objects.filter(job=job, status=CensusImport.PROPOSED).order_by('-id').first()


def reader_apply(user, deal, job, select=None, picks=None):
    """The read's "Use this scan ▸": its import applied as staged, the roster matched as the Census tab's Apply does.
    Runs in landing.apply's transaction (the Deal, then the job, are locked)."""
    imp = waiting_import(job)
    if imp is None:
        raise activity.Refused(NOT_STAGED)
    applied = apply_import(user, imp.id, resolve_job=False)
    people, dependents = applied.stats['rows'], applied.stats['dependents']
    counted = f'{_plural(people, "person", "people")} ({_plural(dependents, "dependent", "dependents")})'
    return landed(imp, applied.activity, counted)


def reader_undo(user, deal, job, force=False):
    """A census import is not undone by the read's ↶ Undo this run: census rows keep keys, never values (rule 4), so
    there is nothing to put back. The person imports the file they want again (the dry run shows what moves)."""
    raise activity.Refused(NO_UNDO)


def reader_discard(user, deal, job):
    """The read's Discard: its waiting import goes with it."""
    imp = waiting_import(job)
    if imp is not None:
        discard_import(user, imp.id, resolve_job=False)
