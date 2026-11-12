"""Issue and Retry, transaction 1 (plan.md §7.12 "Issuing" step 1; J103, J.6.4; OQ35).

Under the Deal lock: the gate (409 with its sentences, `gate.blockers`); quotes stamps the option numbers the files
will print (`stamp_option_numbers` over `line_layout.reading_ids`, the order the client reads them, so every number a
draft predicted is the one stamped); the version is made `building`; the `issue` job is queued in the same
transaction, so the worker can claim it only once this commits and builds outside every lock. The numbers ride an
Activity row of their own, "Stamped n option numbers for proposal vN" (quotes' stamp records none, N.3 #4; never
merged, never reverted: a number is a one-time stamp). A version still building is answered instead of a second one
(a double click); a version left `building` with no job running reads as failed (`selectors.state_of`), so Retry
finds it.
"""

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import APIException, NotFound

from ai import kinds
from ai.services import jobs
from deals import activity
from deals.models import Deal
from quotes import services as plans

from .. import line_layout
from ..models import ProposalIssue
from ..services import AREA
from . import gate, selectors

KEPT = 'Proposal v{version} is issued: its files are kept as the client was sent them. Issue a new version instead.'


class Blocked(activity.Refused):
    """409 {detail, blockers}: every sentence that refuses the issue, all of them joined as `detail`."""

    def __init__(self, sentences):
        self.sentence, self.keys, self.sentences = sentences[0], [], list(sentences)
        APIException.__init__(self, {'detail': ' '.join(sentences), 'blockers': self.sentences})


def _by(user):
    return user if getattr(user, 'is_authenticated', False) else None


def _stamp(user, deal, row):
    """Stamp the numbers and record them; returns {plan id: number}."""
    stamped = plans.stamp_option_numbers(deal, line_layout.reading_ids(deal))
    if stamped:
        count = len(stamped)
        changes = [
            activity.change(f'plan:{pid}', {'plan.option_number': [None, number]})
            for pid, number in sorted(stamped.items())
        ]
        summary = f'Stamped {count} option number{"" if count == 1 else "s"} for proposal v{row.version}'
        activity.record(deal, user, AREA, 'issued', summary, changes=changes, revertible=False)
    return stamped


def _queue(user, deal, row):
    job, _created = jobs.start(user, deal, kinds.ISSUE, params={'issue': row.id, 'version': row.version})
    ProposalIssue.objects.filter(pk=row.pk).update(job=job)  # never save(): an inline run has already moved the row
    return job


def _refuse_unless_ready(deal):
    sentences = gate.blockers(deal)
    if sentences:
        raise Blocked(sentences)


def issue(user, deal):
    """Issue to client: (the version's row, created). Raises Blocked (409)."""
    with transaction.atomic():
        deal = Deal.objects.select_for_update().get(pk=deal.pk)
        going = selectors.building(deal)
        if going is not None:
            return going, False
        _refuse_unless_ready(deal)
        top = ProposalIssue.objects.filter(deal=deal).aggregate(top=Max('version'))['top'] or 0
        row = ProposalIssue.objects.create(deal=deal, version=top + 1, created_by=_by(user))
        _stamp(user, deal, row)
        _queue(user, deal, row)
    return ProposalIssue.objects.get(pk=row.pk), True


def retry(user, deal, version):
    """Build a failed version again, under its own number. 404 for a version the deal has not; 409 for an issued one
    (KEPT) or when the gate refuses now."""
    with transaction.atomic():
        deal = Deal.objects.select_for_update().get(pk=deal.pk)
        row = ProposalIssue.objects.select_for_update().filter(deal=deal, version=version).first()
        if row is None:
            raise NotFound(f'This deal has no proposal v{version}.')
        if row.state == ProposalIssue.ISSUED:
            raise activity.Refused(KEPT.format(version=version))
        if selectors.state_of(row) == ProposalIssue.BUILDING:
            return row
        _refuse_unless_ready(deal)
        row.state, row.error = ProposalIssue.BUILDING, ''
        row.save(update_fields=['state', 'error'])
        _stamp(user, deal, row)
        _queue(user, deal, row)
    return ProposalIssue.objects.get(pk=row.pk)
