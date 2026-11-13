"""Data confidence on the golden deals (Q.9 row 64: GD1, GD6; plan.md §13.10 row 64 "done when"): GD1's two files give
their values to the read as the spec printed them; on a fresh GD6 whose census file arrived, Confirm all on that file
confirms every census cell as one review, the lists name no person, and one Revert puts them all back."""

import json

import pytest

from census.models import Member
from deals import activity
from documents.models import Document
from documents.review_rules import is_approved
from quotes.models import Plan
from review.selectors import confidence as reading
from review.services import marks

pytestmark = pytest.mark.django_db
PERSONAL = ('first_name', 'last_name', 'dob', 'ssn', 'zip')  # who a person is


def test_Q9_64_GD1s_files_carry_their_values_into_the_read(gd1):
    body = reading.confidence(gd1.deal)
    plans = Plan.objects.filter(deal=gd1.deal)
    from_files = sum(1 for plan in plans for key in plan.values if (plan.sources.get(key) or {}).get('doc'))
    assert sum(doc['values'] for doc in body['documents']) == from_files > 0
    assert body['cells']['scanned'] == from_files  # typed from its files: "corrected by hand" (M83)
    assert body['cells']['corrected'] == from_files and body['confirmed']['total'] == 0
    assert body['recheck']['values'] == from_files and body['recheck']['last'] is None


def test_Q9_64_GD6_confirm_all_on_its_census_file_then_one_revert(user, get_to_market):
    built = get_to_market.step('census_arrives').built
    census_file = Document.objects.get(deal=built.deal, kind='census')
    done = marks.mark(user, built.deal.id, 'approve', document_id=census_file.id)
    cells = [entry for person in Member.objects.filter(deal=built.deal) for entry in person.sources.values()]
    assert done.changed == {'census': len(cells)} and all(is_approved(entry) for entry in cells)
    body = reading.confidence(built.deal)
    row = next(doc for doc in body['documents'] if doc['id'] == census_file.id)
    assert row['values'] == row['confirmed'] == len(cells)
    marks.mark(user, built.deal.id, 'ignore', refs=[f'census:{Member.objects.filter(deal=built.deal).first().id}:dob'])
    listed = reading.confidence(built.deal)['ignored']['rows']
    assert listed and all(entry['value'] is None and entry['where'].startswith('Census · ') for entry in listed)
    people = Member.objects.filter(deal=built.deal)
    personal = {str(p.values[key]) for p in people for key in PERSONAL if p.values.get(key)}
    text = json.dumps(listed) + json.dumps(done.row.changes) + done.row.summary
    assert personal and not [value for value in personal if value in text]  # no member data (§3.8)
    activity.revert(done.row.id, user)
    after = [entry for person in Member.objects.filter(deal=built.deal) for entry in person.sources.values()]
    assert sum(1 for entry in after if is_approved(entry)) == 0
