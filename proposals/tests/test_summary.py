"""The Proposal's facts for Agenda and the Overview (plan.md §5.10; I56–I58): the lines that need our recommendation
and how many have it (Issue's own gate), and the newest issued version."""

import pytest

from conftest import make_deal
from proposals import summary
from proposals.models import ProposalIssue
from quotes import services

pytestmark = pytest.mark.django_db


def test_I56_lines_needing_a_recommendation_and_how_many_have_one(user):
    deal = make_deal(user, requested_lines=('medical',))
    services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='HMO 1000', values={})
    quote = services.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='PPO 1500',
                                 values={})  # fmt: skip
    found = summary.facts([deal.id])[deal.id]
    assert (found['needs'], found['picked'], found['ready'], found['latest']) == (1, 0, False, None)
    services.set_recommended(user, quote.id, True)
    found = summary.facts([deal.id])[deal.id]
    assert (found['needs'], found['picked'], found['ready']) == (1, 1, True)
    empty = make_deal(user, name='Empty Co.')
    assert summary.facts([empty.id])[empty.id] == {'latest': None, 'needs': 0, 'picked': 0, 'ready': False}


def test_I57_the_newest_issued_version(user):
    deal = make_deal(user)
    for version, state in ((1, ProposalIssue.ISSUED), (2, ProposalIssue.ISSUED), (3, ProposalIssue.FAILED)):
        ProposalIssue.objects.create(deal=deal, version=version, state=state, created_by=user)
    latest = summary.facts([deal.id])[deal.id]['latest']
    assert latest['version'] == 2
