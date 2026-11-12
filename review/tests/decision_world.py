"""Shared helpers for the review queues' and decisions' tests (slice 55): a link on a deal, the client's answers saved
through the owners' doors with the bases the portal would send, and the link's stamps set by hand (submitted, or
saved some hours ago). All data is synthetic."""

from datetime import timedelta

from census import client_view as census_view
from census.models import Member
from census.services import add_people
from census.services import save_client as census_save
from deals import clock
from intake import client_view as intake_view
from intake.models import Intake
from intake.services import save_client as intake_save
from review.models import ClientLink

from .portal_world import make_request, person

INTAKE_ASKS = {'intake': {'scope': 'all', 'blocks': ['contacts', 'coverage', 'lines']}}
CENSUS_ASKS = {'census': {'scope': 'all'}}


def link_on(user, deal, asks=None, name='Casey (synthetic)'):
    link, _token, _pin = make_request(user, deal, asks or {**INTAKE_ASKS, **CENSUS_ASKS}, people=[{'name': name}])
    return link


def intake_answers(deal, link, answers):
    """The client's intake answers {slot: value}, saved as the portal saves them."""
    deal.refresh_from_db()
    views = intake_view.views(deal, Intake.objects.filter(deal_id=deal.id).first(), link.id)
    sent = {slot: {'value': value, 'base': views[slot][1]} for slot, value in answers.items()}
    saved = intake_save(deal.id, link.id, sent)
    assert not saved.conflicts, saved.conflicts
    return saved


def census_answers(deal, link, cells):
    """The client's census answers {(member id, column): value}, saved as the portal saves them."""
    sent = {}
    for (member_id, column), value in cells.items():
        member = Member.all_objects.get(pk=member_id)
        sent.setdefault(member_id, {})[column] = {'value': value, 'base': census_view.cell(member, column, link.id)[1]}
    saved = census_save(deal.id, link.id, sent, makers=[link.id])
    assert not saved.conflicts, saved.conflicts
    return saved


def added(deal, link, *names):
    """People the client adds on their link, each waiting whole."""
    people = [{'first_name': first, 'last_name': last} for first, last in names]
    return add_people(deal.id, link.id, people, makers=[link.id])


def submitted(link, hours_ago=0):
    """The link saved, then submitted (`hours_ago`)."""
    at = clock.now() - timedelta(hours=hours_ago)
    ClientLink.objects.filter(pk=link.pk).update(last_saved_at=at - timedelta(minutes=1), submitted_at=at)


def idle(link, hours=30):
    ClientLink.objects.filter(pk=link.pk).update(last_saved_at=clock.now() - timedelta(hours=hours), submitted_at=None)


def typing(link):
    ClientLink.objects.filter(pk=link.pk).update(last_saved_at=clock.now(), submitted_at=None)


def employee(user, deal, first='Avery', last='Synthetic', **values):
    return person(user, deal, first, last, **values)


def entry(deal, slot):
    return (Intake.objects.get(deal=deal).client or {}).get(slot)


def cell_entry(member, column):
    return (Member.all_objects.get(pk=member.pk).client or {}).get(column)
