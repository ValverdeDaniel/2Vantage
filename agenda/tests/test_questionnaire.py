"""The medical questionnaire's step on a real deal (I46; slice 58's questionnaires in review): a form asked online on
a link that went out waits on the client, and the client's answers through the link make the step "Review N
questionnaire answers from the client", read from `review.summary`'s `pending.questionnaire`, opening the review
queue's Questionnaire section. Built through the owners' services; every value is synthetic."""

import pytest

from questionnaire.selectors import portal
from questionnaire.services import client as questionnaire_client
from questionnaire.tests.world import make_world

from .world import sent_ask

pytestmark = pytest.mark.django_db
FL = 'fl_blue_51'
FORM_ONLINE = {'questionnaires': [{'form': FL, 'mode': 'online'}]}


@pytest.fixture
def asked(user):
    """(deal, link): a 60-enrolled medical deal whose Florida Blue 51+ form went out yesterday, to fill online."""
    deal = make_world(user)
    return deal, sent_ask(user, deal, asks=FORM_ONLINE, days_ago=1)


def answered(deal, link, values):
    """The client's answers {slot: value} through their link, as the portal saves them."""
    lv = portal.link_view(deal, FL, link.id)
    sent = {slot: {'value': value, 'base': portal.base_of(lv, slot)} for slot, value in values.items()}
    assert not questionnaire_client.save_client(deal.id, link.id, FL, sent).conflicts


def step_row(api, deal):
    rows = api.get(f'/api/deals/{deal.id}/agenda/').json()['rows']
    return next(row for row in rows if row['key'] == 'questionnaire')


def test_I46_a_form_asked_online_waits_on_the_client(api, asked):
    deal, _link = asked
    row = step_row(api, deal)
    assert row['label'] == 'Waiting on the client for the medical questionnaire'
    assert (row['state'], row['section'], row['owner']) == ('waiting', 'waiting', 'client')


def test_I46_S58_the_clients_answers_make_the_step_review_them_in_the_questionnaire_queue(api, asked):
    deal, link = asked
    answered(deal, link, {'txtRsnBid': 'Renewal Increase', 'chkFBPrior': 'No'})
    row = step_row(api, deal)
    assert row['label'] == 'Review 2 questionnaire answers from the client'
    assert (row['state'], row['section'], row['severity']) == ('open', 'up_next', 'warn')
    assert row['link'] == f'/deals/{deal.id}/review?view=queue&section=questionnaire'
    assert row['lead'] is True  # no quotes in yet (OQ90)
