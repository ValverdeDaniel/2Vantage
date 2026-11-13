"""Q.3 #8 for review's marks across owners (plan.md §3.7, O.3.7; slice 64): Confirm all for one file beside a review of
another value on the same plan never deadlocks and both survive — both lock the Deal first, then the plans by id."""

import threading
from unittest import mock

import pytest
from django.db import connection, transaction

from documents.review_rules import is_approved, mark_state
from quotes import services as quotes
from quotes.models import Plan
from quotes.services import file_marks
from quotes.services import review as plan_marks
from review.services import marks

from .confidence_world import world


@pytest.mark.django_db(transaction=True)
def test_Q3_8_confirm_all_beside_a_plan_review_both_survive(user):
    with transaction.atomic():  # the set-up's stored counts are rewritten under their lock
        w = world(user)
        quotes.update_plan(user, w.plan.id, {'values': {'rate_fam': '1600'}})  # typed: no file
    real = file_marks.apply_mark

    def slow(*args):
        out = real(*args)
        threading.Event().wait(0.2)  # hold the locked rows between read and write
        return out

    def confirm_all():
        try:
            marks.mark(user, w.deal.id, 'approve', document_id=w.quote.id)
        finally:
            connection.close()

    def flag_the_typed_rate():
        try:
            plan_marks.mark_values(user, w.deal, 'check', refs=[f'plan:{w.plan.id}:rate_fam'])
        finally:
            connection.close()

    with mock.patch.object(file_marks, 'apply_mark', slow):
        threads = [threading.Thread(target=confirm_all), threading.Thread(target=flag_the_typed_rate)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    plan = Plan.objects.get(pk=w.plan.id)
    assert is_approved(plan.sources['rate_ee']) and mark_state(plan.sources['rate_fam']) == 'check'
    assert plan.flags == 1
