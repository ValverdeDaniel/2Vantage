"""`client_payload(client, viewer)`: the client page's Overview, `GET clients/{id}/overview/` (plan.md §7.16, §8.5;
CL14–CL22, G116; slice 67). Reads only, inside one batch scope over the client's deals (`deals.batch`): agenda's
`facts_for` (every app's `summary.facts` for every deal at once), the carrier forms stored on them, their live files,
the working deal's intake answers, its one headcount and incumbent, commission's card and quotes' line states for the
sold plans. The same queries whatever a deal holds (Q.3 #4); nothing here writes (O.2).

The page works in one deal (`deal_id`): the deal in flight (`current`, the newest not past working with its client),
else the newest; its sections, notes, facts and commission are the page's (old `resolveClientYear`). Version 1 has one
deal per client; a client with none answers every block, empty.

{client_id, deal_id, current: {deal_id, year, stage, effective_date, type, type_label, plans_quoted} | null,
 last_sold: {deal_id, year, carriers, at} | null,
 convert: {allowed, sentence} | null (a prospect's Convert to client, the status door's own answer),
 facts: {deal_id, legal_name, fein, sic_code, situs_state, employees: {value, from, from_label, estimate},
         funding: {value, from}} | null,
 tiles: {effective: {date, days} | null, agenda: {overdue, soon, total}, expected_revenue (whole dollars) | null},
 in_force: {kind, rows} (`in_force.py`), commission: `commission.summary.card` | null,
 outreach: the deal in flight's outreach strip and "Who we've asked" (`payload.outreach_for`) | null,
 history: [{deal_id, year, stage, current, effective_date, sold: {carriers, at} | null, expected | null,
            chips: {intake, census, forms, documents}}] newest first}

The client's name, notes, owner, status, contacts and the status door's moves are deals' own read (`GET clients/{id}/`),
which the page reads beside this one (§7.3).
"""

from django.db.models import Count

from agenda.facts import facts_for
from commission import summary as commission_summary
from deals import batch, clock
from deals import rules as deal_rules
from deals.selectors import status_moves
from documents.models import Document
from intake import selectors as intake_selectors
from questionnaire import forms as questionnaire_forms
from questionnaire.models import Questionnaire
from quotes import facts as quote_facts
from quotes.math import round_money
from quotes.selectors.headcount import WHERE
from quotes.selectors.state import scope_plans

from . import client_agenda, client_rules, rules
from .in_force import in_force
from .payload import outreach_for

MEDICAL = 'medical'
FACT_ANSWERS = ('legal_name', 'fein', 'sic_code', 'situs_state')  # read-only here, "edit in intake ↗" (§8.5)


def client_payload(client, viewer, now=None):
    now = now or clock.now()
    today = clock.today()
    deals = client_rules.newest_first(list(client.deals.select_related('client', 'owner', 'client__owner')))
    ids = [deal.id for deal in deals]
    current = client_rules.current_deal(deals, today)
    anchor = current or (deals[0] if deals else None)
    with batch.scope(ids):
        found = facts_for(ids, now, lost_too=True) if ids else {}
        live = [deal.id for deal in deals if deal.stage != 'lost']
        commission = commission_summary.card(anchor, viewer) if anchor else None
        sold = {deal.id: client_rules.sold_of(scope_plans(deal.id)) for deal in deals}
        history = _history(deals, current, found, sold, anchor, commission)
        newest_sold = next((row for row in history if row['sold']), None)
        return {
            'client_id': client.id,
            'deal_id': anchor.id if anchor else None,
            'current': _current(current, found),
            'last_sold': {'deal_id': newest_sold['deal_id'], 'year': newest_sold['year'], **newest_sold['sold']}
            if newest_sold
            else None,
            'convert': _convert(client, deals),
            'facts': _facts(anchor) if anchor else None,
            'tiles': {
                'effective': client_rules.effective(anchor.effective_date if anchor else None, today),
                'agenda': client_rules.agenda_rollup(client_agenda.open_days(found, live, now, today), today),
                'expected_revenue': round_money(commission['expected']) if commission else None,
            },
            'in_force': in_force(anchor),
            'commission': commission,
            'outreach': outreach_for(current, now) if current else None,
            'history': history,
        }


def _convert(client, deals):
    """Convert to client for a prospect (CL15): allowed or refused with the status door's sentence (§5.1)."""
    moves = status_moves(client, sorted(deals, key=lambda deal: deal.id))
    return rules.client_box({'relationship': client.relationship}, moves)['convert']


def _current(deal, found):
    if deal is None:
        return None
    return {
        'deal_id': deal.id,
        'year': client_rules.year_of(deal),
        'stage': deal.stage,
        'effective_date': deal.effective_date,
        'type': deal_rules.deal_type(deal),
        'type_label': deal_rules.deal_type_label(deal),
        'plans_quoted': (found.get(deal.id) or {}).get('quotes', {}).get('quotes', 0),
    }


def _facts(deal):
    """The header card's facts from the deal the page works in (CL16): its intake answers, the one headcount
    (`quotes.facts.enrolled_headcount`, with where it came from) and the medical funding in force."""
    answers = intake_selectors.answers_of(deal, intake_selectors.intake_row(deal.id))
    headcount = quote_facts.enrolled_headcount(deal)
    incumbent = quote_facts.incumbent(deal, MEDICAL) or {}
    source = headcount.get('source') or None
    return {
        'deal_id': deal.id,
        **{key: str(answers.get(key) if answers.get(key) is not None else '') for key in FACT_ANSWERS},
        'employees': {
            'value': headcount.get('count'),
            'from': source,
            'from_label': WHERE.get(source, '') if source else '',
            'estimate': bool(headcount.get('estimate')),
        },
        'funding': {'value': str(incumbent.get('funding') or ''), 'from': incumbent.get('source')},
    }


def _forms(ids, found):
    """{deal_id: form chips}: each carrier form intake's checklist uses on the deal (armed), and each one stored."""
    started = {}
    for deal_id, key in Questionnaire.objects.filter(deal_id__in=ids).values_list('deal_id', 'form'):
        started.setdefault(deal_id, set()).add(key)
    out = {}
    for deal_id in ids:
        items = (found.get(deal_id) or {}).get('intake', {}).get('items') or []
        armed = {item['form_key']: item.get('signed') for item in items if item.get('form_key')}
        keys = {*armed, *started.get(deal_id, set())}
        forms = {key: questionnaire_forms.get_form(key) for key in keys}
        labels = {key: questionnaire_forms.label(key) for key, form in forms.items() if form}
        kinds = {key: form['kind'] for key, form in forms.items() if form}
        out[deal_id] = client_rules.form_chips(armed, started.get(deal_id, set()), labels, kinds)
    return out


def _history(deals, current, found, sold, anchor, commission):
    """One row per deal, newest first, with G116's chips: the deal's facts, its forms and its live files."""
    ids = [deal.id for deal in deals]
    forms = _forms(ids, found)
    files = dict(
        Document.objects.filter(deal_id__in=ids).values('deal_id').annotate(n=Count('id')).values_list('deal_id', 'n')
    )
    rows = []
    for deal in deals:
        facts = found.get(deal.id) or {}
        rows.append(
            {
                'deal_id': deal.id,
                'year': client_rules.year_of(deal),
                'stage': deal.stage,
                'current': current is not None and deal.id == current.id,
                'effective_date': deal.effective_date,
                'sold': sold.get(deal.id),
                # What the Commission tab expects of the deal the page works in (every deal user sees it, D-066).
                'expected': round_money(commission['expected']) if commission and deal is anchor else None,
                'chips': client_rules.chips(
                    facts.get('intake'), facts.get('census'), forms.get(deal.id, []), files.get(deal.id, 0)
                ),
            }
        )
    return rows
