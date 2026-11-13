"""`review.summary.facts` and the tab's own counts (plan.md §5.10, §8.8; L1, L7, L13, L28, L118; O.6 #3): what the
Waiting lane, the pills, Agenda and the Overview read, counted from the rows themselves."""

from datetime import timedelta
from unittest import mock

import pytest
from django.core.files.base import ContentFile

from deals import clock
from documents.models import Document
from intake.models import Intake
from review import services, summary
from review.models import ClientLink, ReviewNote
from review.rules import badges

pytestmark = pytest.mark.django_db

ASK = {'asks': {'intake': {'scope': 'missing'}}}


def make(user, deal, people=({'name': 'Dana'},)):
    return services.create(user, deal.id, {**ASK, 'people': list(people)})


def test_L118_a_deal_with_no_request_has_quiet_facts(user, deal):
    found = summary.facts([deal.id])[deal.id]
    assert found['open'] == 0 and found['waiting'] == [] and found['response'] is None
    assert badges.counts(found) == {'to_send': 0, 'to_review': 0, 'waiting': 0, 'questions': 0}
    assert summary.facts([deal.id + 10_000]) == {}


def test_L7_a_new_request_waits_until_it_is_sent_and_answered(user, deal):
    made = make(user, deal, people=({'name': 'Dana'}, {'name': 'Sam'}))
    link = made.links[0][0]
    found = summary.facts([deal.id])[deal.id]
    assert found['requests']['draft'] == 1 and found['open'] == 1
    assert found['waiting'][0]['names'] == ['Dana', 'Sam'] and found['waiting'][0]['asks'] == ['Intake gaps']
    assert badges.counts(found)['waiting'] == 1
    services.mark_sent(user, link.id, copied=True)
    found = summary.facts([deal.id])[deal.id]
    assert found['waiting'][0]['state'] == 'partly_sent' and found['first_sent_at']
    assert found['response']['state'] == 'waiting'
    ClientLink.objects.filter(pk=link.pk).update(last_saved_at=clock.now())
    found = summary.facts([deal.id])[deal.id]
    assert found['response']['state'] == 'answering' and found['in_progress'][0]['name'] == 'Dana'
    assert badges.counts(found)['waiting'] == 2  # the request, and Dana still answering
    ClientLink.objects.filter(pk=link.pk).update(submitted_at=clock.now() + timedelta(minutes=1))
    found = summary.facts([deal.id])[deal.id]
    assert found['requests']['answered'] == 1 and found['open'] == 0
    assert found['response'] == {'state': 'answered', 'at': mock.ANY, 'link_id': link.id, 'name': 'Dana'}


def test_L7_turning_the_only_sent_link_off_takes_the_request_out_of_waiting(user, deal):
    link = make(user, deal).links[0][0]
    services.mark_sent(user, link.id)
    services.revoke(user, link.id)
    found = summary.facts([deal.id])[deal.id]
    assert found['requests']['expired'] == 1 and found['waiting'] == []


def test_L13_to_review_counts_what_came_back_and_waits_on_us(user, deal):
    link = make(user, deal).links[0][0]
    stamp = clock.now() - timedelta(hours=30)
    ClientLink.objects.filter(pk=link.pk).update(sent_at=stamp, last_saved_at=stamp)
    Intake.objects.update_or_create(
        deal=deal,
        defaults={
            'client': {
                'sic_code': {'value': '1234', 'link': link.id, 'status': 'pending'},
                'dba': {'value': 'Co', 'link': link.id, 'status': 'approved'},
            }
        },
    )
    Document.objects.create(
        deal=deal, file=ContentFile(b'x', name='from-client.pdf'), original_name='f.pdf', kind='claims', source='client'
    )
    ReviewNote.objects.create(deal=deal, surface='intake', key='sic_code', kind='question', text='?', at=clock.now())
    ReviewNote.objects.create(deal=deal, surface='intake', key='dba', kind='ask', author=user, at=clock.now())
    found = summary.facts([deal.id])[deal.id]
    assert found['pending'] == {'intake': 1, 'census': 0, 'people': 0, 'questionnaire': 0, 'documents': 1, 'total': 2}
    # saved 30 hours ago and left: ready for review
    assert found['ready'] == {'intake': 1, 'census': 0, 'questionnaire': 0}
    intake = found['sections']['intake']
    assert (intake['to_review'], intake['ready_idle'], intake['ready_submitted']) == (1, 1, 0)
    assert (intake['questions'], intake['in_tray']) == (1, 1)
    assert found['questions']['open'] == 1 and found['questions']['oldest_at']
    assert badges.counts(found) == {'to_send': 1, 'to_review': 3, 'waiting': 1, 'questions': 1}  # idle: not typing


def test_L69_a_due_nudge_is_counted(user, deal):
    link = make(user, deal).links[0][0]
    ClientLink.objects.filter(pk=link.pk).update(nudge={'on': clock.today().isoformat()}, sent_at=clock.now())
    assert summary.facts([deal.id])[deal.id]['nudges'] == 1
