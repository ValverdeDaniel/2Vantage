"""An issue's end, transaction 2 (plan.md §7.12 "Issuing" step 3; J102, J103, J.6.4; O.3.7).

- `store(job, issue_id, files)`: the built files stored as protected Documents of kind `proposal` ("Proposal vN ·
  Client PDF"; never screened, `documents.services.store_bytes`), the version `issued`, the deal moved to Proposal
  (`deals.services.advance`: forward only, a lost deal stays lost), and one Activity row "Issued proposal vN" naming
  the PDF, never merged and never reverted. Locks the Deal, then the version.
- `fail(job, issue_id, sentence)`: the version `failed`, with the sentence the packet card shows beside Retry, and one
  Activity row "Proposal vN could not be built".
Both change nothing on a version that is no longer building (a Retry raced, or it ended before). The bytes go to
storage as each Document is made; a transaction that fails after leaves them for `sweep_orphan_files` (E98), as
signing's filed copy does.
"""

from django.db import transaction

from deals import activity, clock
from deals.models import Deal
from deals.services import advance
from documents.services import store_bytes

from ..models import ProposalIssue
from ..services import AREA
from .catalog import FILE_KEYS, LABELS

KIND = 'proposal'
REASON = 'a proposal was issued'


def target(row):
    return f'proposal_issue:{row.id}'


def _locked(job, issue_id):
    deal = Deal.objects.select_for_update().get(pk=job.deal_id)
    return deal, ProposalIssue.objects.select_for_update().get(pk=issue_id)


@transaction.atomic
def store(job, issue_id, files):
    """`files`: {key: (file name, bytes)} for every key of FILE_KEYS. Returns (the row, its Activity row or None)."""
    user = job.created_by
    deal, row = _locked(job, issue_id)
    if row.state != ProposalIssue.BUILDING:
        return row, None
    diff = {'state': [row.state, ProposalIssue.ISSUED]}
    for key in FILE_KEYS:
        name, data = files[key]
        label = f'Proposal v{row.version} · {LABELS[key]}'
        document = store_bytes(user, deal, name, data, KIND, label, protected=True)
        setattr(row, key, document)
        diff[key] = [None, document.id]
    row.state, row.error, row.job = ProposalIssue.ISSUED, '', job
    row.issued_at, row.issued_by = clock.now(), user
    row.save()
    advance(deal, user, 'proposal', REASON)
    written = activity.record(
        deal,
        user,
        AREA,
        'issued',
        f'Issued proposal v{row.version}',
        changes=[activity.change(target(row), diff)],
        document_id=row.pdf_id,
        revertible=False,
    )
    return row, written


@transaction.atomic
def fail(job, issue_id, sentence):
    """Returns the Activity row, or None when the version was no longer building."""
    deal, row = _locked(job, issue_id)
    if row.state != ProposalIssue.BUILDING:
        return None
    row.state, row.error, row.job = ProposalIssue.FAILED, sentence[:300], job
    row.save(update_fields=['state', 'error', 'job'])
    return activity.record(
        deal,
        job.created_by,
        AREA,
        'failed',
        f'Proposal v{row.version} could not be built',
        changes=[activity.change(target(row), {'state': [ProposalIssue.BUILDING, ProposalIssue.FAILED]})],
        revertible=False,
    )
