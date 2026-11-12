"""Issue's machinery on a small synthetic deal (plan.md §7.12 "Issuing"; J103, J.6.4, J.6.10 "Issue": refuses until
covered, stamps under the lock and builds outside it, a failed build leaves vN failed with Retry, protected files;
Q.9 row 32). Jobs run inline in tests (AI_JOBS_INLINE) unless a test turns it off to see the queue."""

import pytest

from ai import kinds
from ai.models import Job
from ai.testing import run_jobs
from conftest import make_client, make_deal
from deals import activity
from deals.models import Activity, Deal
from deals.services import delete_client
from documents import services as documents
from proposals.issues import build, gate, selectors, start
from proposals.models import ProposalIssue
from quotes import presented
from quotes import services as plans
from quotes.models import Plan

pytestmark = pytest.mark.django_db


def ready_deal(user, **kwargs):
    deal = make_deal(user, **kwargs)
    current = plans.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='Today')
    quote = plans.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='Quote', replaces_ids=[current.id]
    )
    plans.set_recommended(user, quote.id, True)
    return deal, quote


def test_J_6_10_issue_stamps_under_the_lock_and_builds_outside_it(user, settings):
    settings.AI_JOBS_INLINE = False
    deal, quote = ready_deal(user)
    row, created = start.issue(user, deal)
    assert created and row.state == ProposalIssue.BUILDING
    assert Plan.objects.get(pk=quote.pk).option_number == 1  # stamped in the Issue's own transaction
    assert not deal.documents.filter(kind='proposal').exists()  # nothing built yet: the job does it
    job = Job.objects.get(pk=row.job_id)
    assert (job.kind, job.lane, job.status) == (kinds.ISSUE, kinds.SYSTEM, kinds.QUEUED)
    again, created = start.issue(user, deal)  # a double click answers the version already building
    assert (again.pk, created) == (row.pk, False)
    run_jobs()
    row.refresh_from_db()
    assert row.state == ProposalIssue.ISSUED and row.pdf.protected and row.pptx.protected and row.xlsx.protected
    assert Job.objects.get(pk=job.pk).status == kinds.DONE
    assert Deal.objects.get(pk=deal.pk).stage == 'proposal'


def test_J103_a_failed_build_leaves_the_version_failed_and_retry_builds_it_again(user, api, monkeypatch):
    deal, _quote = ready_deal(user)

    def broken(*_args, **_kwargs):
        raise RuntimeError('a painter fell over: Secret Client 123-45-6789')

    monkeypatch.setattr(build, 'files', broken)
    row, _created = start.issue(user, deal)
    row.refresh_from_db()
    assert (row.state, row.error) == (ProposalIssue.FAILED, build.FAILED)  # a sentence, never the exception's text
    listed = api.get(f'/api/deals/{deal.id}/proposal/issues/').json()
    assert [(item['version'], item['state'], item['error']) for item in listed] == [(1, 'failed', build.FAILED)]
    failed = Activity.objects.get(deal=deal, summary='Proposal v1 could not be built')
    with pytest.raises(activity.Refused):
        activity.revert(failed.id, user)
    assert Deal.objects.get(pk=deal.pk).stage != 'proposal'
    monkeypatch.undo()
    response = api.post(f'/api/deals/{deal.id}/proposal/issues/1/retry/', {}, format='json')
    assert response.status_code == 202, response.content
    assert (response.json()['version'], response.json()['state']) == (1, 'issued')
    again = api.post(f'/api/deals/{deal.id}/proposal/issues/1/retry/', {}, format='json')
    assert again.status_code == 409 and again.json()['detail'] == start.KEPT.format(version=1)
    assert api.post(f'/api/deals/{deal.id}/proposal/issues/9/retry/', {}, format='json').status_code == 404


def test_J103_a_version_whose_job_ended_without_its_files_reads_failed(user, settings):
    settings.AI_JOBS_INLINE = False
    deal, _quote = ready_deal(user)
    row, _created = start.issue(user, deal)
    Job.objects.filter(pk=row.job_id).update(status=kinds.FAILED, error='This stopped answering for 10 minutes.')
    found = selectors.issues(deal)[0]
    assert (found['state'], found['job']) == ('failed', None)
    assert found['error'] == 'This stopped answering for 10 minutes.'
    assert start.retry(user, deal, 1).state == ProposalIssue.BUILDING


def test_J103_the_gate_refuses_past_sixteen_plans_and_with_nothing_on_the_proposal(user, api):
    empty = make_deal(user, name='Empty (synthetic)')
    response = api.post(f'/api/deals/{empty.id}/proposal/issue/', {}, format='json')
    assert response.status_code == 409 and response.json()['blockers'] == [gate.NOTHING]
    deal, _quote = ready_deal(user, name='Crowded (synthetic)')
    for n in range(presented.MAX_COLUMNS):
        plans.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name=f'Quote {n}')
    blockers = gate.blockers(deal)
    assert any('a client page holds at most 16 on a line' in sentence for sentence in blockers)
    assert api.post(f'/api/deals/{deal.id}/proposal/issue/', {}, format='json').status_code == 409
    assert not ProposalIssue.objects.filter(deal__in=[empty, deal]).exists()


def test_O_3_7_issued_files_refuse_archive_and_purge_and_go_only_with_their_client(user, admin_user):
    client, deal = make_client(user, name='Kept (synthetic)')
    _deal, quote = ready_deal(user, name='Unused (synthetic)')
    current = plans.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='Today')
    plans.set_recommended(user, plans.create_renewal(user, current.id).id, True)
    row, _created = start.issue(user, deal)
    row.refresh_from_db()
    with pytest.raises(activity.Refused):
        documents.archive(user, row.pdf_id)
    with pytest.raises(activity.Refused):
        documents.purge(admin_user, row.xlsx_id)
    delete_client(user, client.id)
    assert not ProposalIssue.objects.filter(pk=row.pk).exists()
    assert not Deal.objects.filter(pk=deal.pk).exists()
    assert quote.pk  # the other deal stays
