"""Set-up for the data-confidence tests (plan.md §8.6; M83–M91; slice 64): one deal whose values came from two
synthetic files on every owner — intake, census, quotes and a questionnaire — the way reads land them (origin `ai`,
the file and page, Claude's doubt), written straight onto the rows as test set-up standing in for the readers, which
these tests do not exercise. Each owner's stored counts are rewritten after, so they start right (Q.3 #9).

Canary strings sit in the member data (a census name, a questionnaire answer, a laser) so a test can prove none of
them reaches the confidence read, Activity or an error (§3.8, Q.8). Every name and number is invented.
"""

from types import SimpleNamespace

from census import facts as census_facts
from census.models import Member
from deals.values import apply, source
from intake import flags as intake_flags
from intake.models import Intake
from questionnaire import services as forms
from questionnaire.models import Questionnaire
from questionnaire.selectors import context
from questionnaire.services import common
from questionnaire.tests.world import make_world
from quotes import services as quotes
from quotes.models import Plan
from quotes.tests.review_world import add_file, read_into

FL = 'fl_blue_51'
CANARY_NAME = 'Zyxwvutski'  # a member's last name (PHI)
CANARY_ANSWER = 'Canary Suite 4711'  # a questionnaire answer (member data, §3.8)
CANARY_LASER = 'ID-9931 $85,000'  # a laser (PHI)


def _read(doc, low=()):
    def entry(key):
        return source('ai', None, doc=doc.id, page=1, low='two figures' if key in low else None)

    return entry


def _intake(deal, doc):
    row = Intake.objects.get(deal=deal)
    apply(row.answers, row.sources, {'fein': '00-1112223', 'sic_code': '3441'}, _read(doc, low=('sic_code',)))
    intake_flags.stamp(deal, row)
    row.save()
    return row


def _census(deal, doc):
    people = []
    for position, (last, dob) in enumerate([(CANARY_NAME, '01/15/1980'), ('Sampleton', '02/02/1981')]):
        person = Member(deal=deal, kind='employee', position=position, values={}, sources={})
        apply(person.values, person.sources, {'last_name': last, 'dob': dob}, _read(doc, low=('dob',)))
        person.save()
        people.append(person)
    census_facts.refresh(deal.id)
    return people


def _form(user, deal, doc):
    forms.set_answers(user, deal.id, FL, {'txtRsnBid': 'Renewal Increase'})  # typed: no file
    row = Questionnaire.objects.get(deal=deal, form=FL)
    apply(row.answers, row.sources, {'txtAdd2': CANARY_ANSWER}, _read(doc))
    common.restamp(row, context.prefill_facts(deal))
    row.save()
    return row


def world(user):
    """`deal` with `quote` (a file) read into a medical plan (one value doubted), intake (SIC doubted), two people
    (birth dates doubted) and a form; `other` (a second file) read into the stop-loss line, its laser included; a
    typed plan value and a typed form answer with no file."""
    deal = make_world(user, lines=('medical', 'stop_loss'))
    quote, other = add_file(user, deal), add_file(user, deal, name='stop-loss (synthetic).pdf')
    plan = quotes.create_plan(user, deal, line='medical', role='alternate', carrier='Cigna', name='Open Access')
    read = {'rate_ee': '512.34', 'deductible_single': '1500', 'network': 'OAP'}
    plan = read_into(plan, read, quote, low=('rate_ee',))
    stop = quotes.create_plan(user, deal, line='stop_loss', role='alternate', carrier='Sun Life', name='Spec 50k')
    stop = read_into(stop, {'sl_spec_deductible': '50000', 'sl_lasers': CANARY_LASER}, other)
    current = Plan.objects.get(deal=deal, role='current')
    intake = _intake(deal, quote)
    people = _census(deal, quote)
    form = _form(user, deal, quote)
    return SimpleNamespace(
        deal=deal, quote=quote, other=other, plan=plan, stop=stop, current=current, intake=intake, people=people,
        form=form,
    )  # fmt: skip
