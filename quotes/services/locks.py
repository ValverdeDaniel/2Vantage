"""The lock order of quotes' writes (plan.md §3.7, O.3.7): the Deal row first, then plans by id.

A rule over several plans (the cap, order, slots, roles, links, enrollment) takes the Deal row, then the plans it
reads and writes, so two such rules on one deal run one after the other and the cap holds (Q.3 #8). A value edit
locks only its plan. Every helper runs inside the caller's transaction.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals.models import Deal

from ..models import Plan
from ..selectors.state import line_data, replaced_ids


def _in_transaction():
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("quotes' locks run inside transaction.atomic()")


def deal(deal_id):
    _in_transaction()
    return Deal.objects.select_for_update().get(pk=deal_id)


def _with_links(plans):
    links = replaced_ids(from_plan_id__in=[plan.id for plan in plans])
    for plan in plans:
        plan.replaces_ids = sorted(links.get(plan.id, []))
    return plans


def plans(deal_row, ids):
    """The plans `ids` names, locked by id; 400 when one is not a live plan on this deal."""
    _in_transaction()
    ids = sorted(set(ids))
    rows = list(Plan.objects.select_for_update().filter(deal=deal_row, id__in=ids).order_by('id'))
    if len(rows) != len(ids):
        raise ValidationError({'plan_ids': ['A plan is not on this deal.']})
    return _with_links(rows)


def line(deal_row, line_key):
    """({id: plan} for every live plan on the line, locked by id; the line as `LineData`, in layout order)."""
    _in_transaction()
    rows = _with_links(list(Plan.objects.select_for_update().filter(deal=deal_row, line=line_key).order_by('id')))
    return {plan.id: plan for plan in rows}, line_data(line_key, rows)


def plan_deal(plan_id):
    """The Deal of a plan, locked: the first lock of a write that starts from a plan id. 404 for an unknown plan."""
    deal_id = Plan.objects.filter(pk=plan_id).values_list('deal_id', flat=True).first()
    if deal_id is None:
        raise Plan.DoesNotExist
    return deal(deal_id)
