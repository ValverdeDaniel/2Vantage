"""What Agenda's services share (plan.md §3.7; O.3.7): the Activity area, targets, the lock order and the refusal.

Every write locks the Deal first (the one lock order across rows and owners), then its own row, and records Activity
in area `agenda` with before and after per key: a mark's `kind`, `until` and `sig`; a task's `due`, `done`,
`assigned_to` and `deleted`. Titles, notes and counts never reach Activity (I.6, I.5 bug 16): an edit of a task's
title or note records the key alone. Summaries use the catalogue's step titles, never a row's live words.
"""

from rest_framework.exceptions import ValidationError

from deals import activity
from deals.models import Deal

AREA = 'agenda'


def mark_target(step_key):
    return f'mark:{step_key}'


def task_target(task_id):
    return f'task:{task_id}'


def lock_deal(deal_id):
    """The Deal row, locked (raises Deal.DoesNotExist)."""
    return Deal.objects.select_for_update().get(pk=deal_id)


def refuse(status, sentence):
    """A refusal as its HTTP answer: 400 for a request that could never work, 409 for the deal's state."""
    if status == 409:
        raise activity.Refused(sentence)
    raise ValidationError({'detail': sentence})


def record(deal, user, action, summary, changes, **more):
    return activity.record(deal, user, AREA, action, summary, changes=changes, **more)
