"""One deal's questionnaire facts, read once per request (G.4; P6: the old app read prefill on every seed and answers
three times per payload).

`deal_context(deal)` is cheap: the checklist choices, the one headcount (`quotes.facts.enrolled_headcount`), the two
items resolved (`choice.resolve_all`) and the stored questionnaires. `prefill_facts(deal)` reads the group facts
(`quotes.facts.group_facts`) and the current medical plans with their renewals, only when a form's values are needed.
`form_view(...)` puts one form together: its stored JSON (or the starting rows of a form nobody wrote), its live
prefill and the engine's view.
"""

from collections import namedtuple

from deals import batch
from intake import selectors as intake_selectors
from quotes import facts as quote_facts
from quotes.fields import TIER_RATE_KEYS
from quotes.models import Plan

from .. import choice, forms, prefill, values
from ..models import Questionnaire

Context = namedtuple('Context', 'deal checklist headcount resolved stored')
FormView = namedtuple('FormView', 'form row stored prefill view')


def _stored(ids):
    return batch.grouped(Questionnaire.objects.filter(deal_id__in=ids), lambda row: row.deal_id)


def deal_context(deal):
    intake = intake_selectors.intake_row(deal.id)
    checklist = (intake.checklist if intake else None) or {}
    headcount = quote_facts.enrolled_headcount(deal)
    resolved = choice.resolve_all(checklist, headcount['count'], deal.requested_lines)
    stored = {row.form: row for row in batch.per_deal('questionnaire.rows', deal.id, _stored, ())}
    return Context(deal, checklist, headcount, resolved, stored)


def started(row):
    """A form is started once it holds an answer, a client entry or a signature (G7)."""
    return bool(row and (row.answers or row.client or row.officer_signed_at or row.agent_signed_at))


def started_forms(ctx):
    return {key: started(row) for key, row in ctx.stored.items()}


def armed(ctx, form_key):
    return any(r['form'] == form_key for r in ctx.resolved.values())


def chips(ctx):
    return choice.chips(ctx.resolved, started_forms(ctx))


def _current_rows(ids):
    plans = Plan.objects.filter(deal_id__in=ids, line='medical', role__in=('current', 'renewal'))
    rows = plans.order_by('sort_order', 'id').values('deal_id', 'id', 'role', 'name', 'renews_id', 'values')
    return batch.grouped(rows, lambda row: row.pop('deal_id'))


def current_plans(deal):
    """{plan id: {name, effective_date, rate_ee…rate_fam, renewal: {…}}} and the ids in slot order: the deal's current
    medical plans (`ordered_plans` order: slot order) and their renewals (G30, G134)."""
    plans = list(batch.per_deal('questionnaire.current_plans', deal.id, _current_rows, ()))
    renewals = {p['renews_id']: p for p in plans if p['role'] == 'renewal' and p['renews_id']}

    def facts_of(plan):
        found = {'name': plan['name']}
        found.update({key: str((plan['values'] or {}).get(key) or '') for key in TIER_RATE_KEYS})
        return found

    out, order = {}, []
    for plan in plans:
        if plan['role'] != 'current':
            continue
        renewal = renewals.get(plan['id'])
        out[plan['id']] = {**facts_of(plan), 'renewal': facts_of(renewal) if renewal else {}}
        order.append(plan['id'])
    return out, order


def prefill_facts(deal):
    """(prefill facts, current plan ids in order) for every form on the deal."""
    group = quote_facts.group_facts(deal)
    plans, order = current_plans(deal)
    effective = group.get('deal.medical_effective_date') or ''
    for plan in plans.values():
        plan['effective_date'] = effective
    sic_table = forms.FORMS['fl_blue_51']['tables']['sic_codes']
    return prefill.facts(group, plans, sic_table), order


def form_view(form_key, row, facts_and_order):
    """FormView(form, row, stored, prefill values, engine view) for one form."""
    form = forms.FORMS[form_key]
    found_facts, order = facts_and_order
    starting, _last = prefill.starting_rows(form, order)
    stored = values.stored_of(row, starting)
    live = prefill.values(form, found_facts, stored.rows)
    return FormView(form, row, stored, live, values.shown(form, stored, live))
