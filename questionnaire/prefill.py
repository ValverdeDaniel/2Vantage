"""Live prefill: every slot nobody wrote shows what the deal already knows (plan.md §6.8; G27–G31, G134). Pure.

`facts(group, plans, sic_table)` turns `quotes.facts.group_facts` and the current medical plans into the prefill keys
the specs name (`prefill` on a field), and `values(form, facts, rows)` gives {slot: value} for one form. Only
unambiguous facts: Q16, the contributions and every medical answer are never prefilled (G29), and Q15's premiums are
typed by staff (OQ56 default). Fixes over the old app: no 'FL' fallback for the state (B7); the carrier comes from the
medical line only (N1); the SIC code fills only from a leading four-digit code found in the carrier's table, never a
NAICS code; Warner's waiting period, years in business and agent of record fill from intake and the BOR on file (G31).

A row started for a current plan (`plan` on the row) follows that plan: its unwritten slots read the plan's name, its
effective date and, on Warner's grids, its tier rates or its renewal's, copied as they are (G134).
"""

import re

_SIC = re.compile(r'^\s*(\d{4})(?!\d)')


def sic_pair(text, table):
    """(code, description) from a typed SIC: its leading four-digit code when the carrier's table has it, else
    ('', ''). "3441 — Fabricated Structural Metal" fills; a six-digit NAICS code or a description alone does not."""
    found = _SIC.match(str(text or ''))
    if not found:
        return '', ''
    code = found.group(1)
    return next(((c, d) for c, d in table if c == code), ('', ''))


def facts(group, plans=None, sic_table=()):
    """{prefill key: value} from the group facts, plus `plans`: {plan id: {name, effective_date, rate_ee…rate_fam,
    renewal: {…}}} for the current medical plans."""
    code, description = sic_pair(group.get('group.sic'), sic_table)
    carrier = group.get('group.current_carrier') or ''
    return {
        'legal_name': group.get('group.legal_name') or '',
        'anniversary_date': group.get('deal.anniversary_date') or '',
        'address_street': group.get('group.address_street') or '',
        'address_city': group.get('group.address_city') or '',
        'address_state': group.get('group.address_state') or group.get('group.situs_state') or '',
        'address_zip': group.get('group.zip') or '',
        'sic_code': code,
        'sic_description': description,
        'fein': group.get('group.fein') or '',
        'atne': group.get('group.atne') or '',
        'eligible_employees': group.get('group.eligible') or '',
        'current_carrier': carrier,
        'replacing_coverage': 'Yes' if carrier else '',
        'officer_name': group.get('group.contact_name') or '',
        'officer_title': group.get('group.contact_title') or '',
        'phone': group.get('group.contact_phone') or '',
        'agent_name': group.get('broker.agent') or '',
        'agency_name': group.get('broker.agency') or '',
        'waiting_period': group.get('group.waiting_period') or '',
        'years_in_business': group.get('group.years_in_business') or '',
        'agent_of_record': 'Yes' if group.get('broker.is_bor') else '',
        'plans': plans or {},
    }


def _plan_value(facts, plan_id, name):
    """`plan.<fact>` or `renewal.<fact>` for the plan a row was started for."""
    which, _, fact = name.partition('.')
    plan = (facts.get('plans') or {}).get(plan_id) or {}
    if which == 'renewal':
        plan = plan.get('renewal') or {}
    value = plan.get(fact)
    return '' if value is None else str(value)


def values(form, facts, rows):
    """{slot: value} for every slot the deal can fill now; blanks are left out."""
    from .engine.spec import block_fields, section_fields
    from .slots import key

    out = {}
    for field in section_fields(form):
        name = field.get('prefill')
        value = str(facts.get(name) or '') if name else ''
        if value:
            out[field['key']] = value
    for block_key in (form.get('blocks') or {}).keys():
        fields = [f for f in block_fields(form, block_key) if f.get('prefill')]
        for row in rows.get(block_key) or []:
            if not row.get('plan'):
                continue
            for field in fields:
                value = _plan_value(facts, row['plan'], field['prefill'])
                if value:
                    out[key(block_key, row['id'], field['key'])] = value
    return out


def starting_rows(form, plan_ids):
    """The rows a form starts with (G.6): one per current medical plan on a block that follows them, up to its
    maximum, then blank rows up to its minimum. Ids run 1..n across the form in block order. Returns (rows, last id)."""
    rows, last = {}, 0
    for block_key, block in (form.get('blocks') or {}).items():
        planned = list(plan_ids)[: block.get('max_rows', 1)] if block.get('rows_from') == 'current_medical' else []
        out = []
        for plan_id in planned:
            last += 1
            out.append({'id': last, 'origin': 'prefill', 'plan': plan_id})
        while len(out) < block.get('min_rows', 0):
            last += 1
            out.append({'id': last, 'origin': 'form'})
        rows[block_key] = out
    return rows, last
