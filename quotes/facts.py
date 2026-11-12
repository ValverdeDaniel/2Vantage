"""What the board says about one plan, worked out on the server (plan.md §5.4; F62, F122, D-051). Pure.

- `statuses`: per field, `missing` (required and blank) or `to_check` (an open warning); blank and ok keys are left
  out. A plan with a quoted premium and no tier rate at all is not missing its tier rates (age-banded medical, §5.5).
- `open_warning` is `documents.review_rules.open_warning`, the one rule (slice 17, OQ28): a value marked ⚑ Needs
  checking, or one Claude read and doubted (or the locator could not find) that nobody has approved or ignored.
- `plan_facts`: `incomplete` (a key field of the line blank or to check: what "Hide incomplete data" hides; a missing
  total is not, F22: the filter card names plans with no price instead, F140), `flags` (open warnings on the plan),
  `compliance` (the tests the carrier says it fails: minimum value and Medicare Part D; a blank answer is not a
  failure) and `numbers`.
- `numbers`: the plan's numeric values as numbers, parsed once here so the board's sliders, caps and rules compare
  the server's reading (F20, F21, F24). Strict: one number, with an optional $ and thousands commas, and % only on a
  percent field; a range ("$25 – $135"), a phrase or a blank is no number, and no number never meets a filter.
- `incumbent` (F144): the carrier and funding in force on a line, the one read RFP, commission and the Overview call;
  it reads the database (`selectors/intake_facts.py`), unlike the rest of this module.
- `enrolled_headcount`, `headcount` and `enrollment_check` (§5.7; O.6 #24, #25): the one headcount and its
  cross-check, also database reads (`selectors/headcount.py`).
- `group_facts` (§5.7, K101; slice 42): the group's facts the carrier forms print, read once per request; the
  questionnaire prefills from them and rfp prints them. `split_address` is its address parser.
"""

import re
from functools import cache

from deals import lines
from documents.review_rules import open_warning

from . import fields

# The fields that make a plan complete, per field set (the old Advisor's KEY_FIELDS_BY_SET).
KEY_FIELDS = {
    'medical': ['deductible_single', 'oop_max_single', 'network', 'plan_type'],
    'dental': ['den_annual_max', 'den_deductible', 'network', 'plan_type'],
    'vision': ['vis_exam_copay', 'vis_frame_allowance', 'network', 'plan_type'],
    'life': ['life_schedule', 'life_guarantee_issue', 'unit_rate'],
    'disability': ['dis_elimination', 'dis_benefit_pct', 'dis_max_benefit', 'unit_rate'],
    'generic': ['benefit_summary', 'plan_type', 'unit_rate'],
    'stop_loss': ['sl_spec_deductible', 'sl_spec_rate', 'sl_agg_factor', 'sl_agg_corridor'],
}
COMPLIANCE = ('minimum_value', 'part_d_creditable')
NUMERIC = ('amount', 'percent', 'rate', 'rate4', 'number')
_NUMBER = re.compile(r'^\$?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*(%?)$')


@cache
def _line_keys(line_key):
    return tuple(fields.keys_for(line_key))


@cache
def _numeric_keys(line_key):
    numeric = [key for key in _line_keys(line_key) if fields.BY_KEY[key]['type'] in NUMERIC]
    return tuple((key, fields.BY_KEY[key]['type'] == 'percent') for key in numeric)


@cache
def _key_fields(line_key):
    has = set(_line_keys(line_key))
    return tuple(
        key for key in KEY_FIELDS.get(lines.BY_KEY[line_key]['field_set'], KEY_FIELDS['generic']) if key in has
    )


def statuses(line_key, values, sources):
    quoted_only = values.get('group_premium_monthly') and not any(values.get(k) for k in fields.TIER_RATE_KEYS)
    status = {}
    for key in _line_keys(line_key):
        if values.get(key) in (None, ''):
            exempt = quoted_only and key in fields.TIER_RATE_KEYS
            if fields.BY_KEY[key]['required'] and not exempt:
                status[key] = 'missing'
        elif open_warning(sources.get(key)):
            status[key] = 'to_check'
    return status


def number(value, percent=False):
    """One stored value as a number, or None: '3300', '$1,500', '612.50' and (on a percent field) '20%' are numbers;
    '$25 – $135', 'Deductible, then 20%' and '' are not."""
    found = _NUMBER.match(str(value if value is not None else '').strip())
    if not found or (found.group(2) and not percent):
        return None
    out = float(found.group(1).replace(',', ''))
    return int(out) if out == int(out) else out


def numbers(line_key, values):
    """{key: number} for the line's numeric fields that hold one number."""
    out = {}
    for key, percent in _numeric_keys(line_key):
        parsed = number(values.get(key), percent)
        if parsed is not None:
            out[key] = parsed
    return out


def plan_facts(line_key, values, status):
    """Judged against the fields the line has: a dental plan has no deductible and out-of-pocket max to miss."""
    keys = _key_fields(line_key)
    blank = any(values.get(key) in (None, '') for key in keys)
    doubtful = any(status.get(key) == 'to_check' for key in keys)
    return {
        'incomplete': blank or doubtful,
        'flags': sum(1 for state in status.values() if state == 'to_check'),
        'compliance': [key for key in COMPLIANCE if str(values.get(key) or '').strip().lower() == 'no'],
        'numbers': numbers(line_key, values),
    }


def incumbent(deal, line):
    """{carrier, funding, source} in force on a line: its current plans once the Advisor has them, else intake's
    current-coverage row; None when neither says (F144, §6.5)."""
    from .selectors.intake_facts import incumbent as read

    return read(deal, line)


def enrolled_headcount(deal):
    """{count, source, estimate, via}: the Advisor's medical enrollment, else intake's enrolled count, else its eligible
    or total count as an estimate (§5.7, OQ21)."""
    from .selectors.headcount import enrolled_headcount as read

    return read(deal)


def headcount(deal_id):
    """`intake.providers.headcount`: {count, source, estimate}."""
    from .selectors.headcount import headcount as read

    return read(deal_id)


def enrollment_check(deal):
    """{intake, census, advisor, used, differ, warning}: the three answers to "how many are enrolled" (K19, M67)."""
    from .selectors.headcount import enrollment_check as read

    return read(deal)


# ---- group facts (§5.7; K101, G28): what the carrier forms, cover pages and emails print about the group ------------

_ADDRESS = re.compile(r'^(.*?),\s*([^,]+?),?\s+([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)\s*$')


def split_address(text):
    """'street, city, ST 12345' -> (street, city, state, zip, city_state_zip). An address it cannot read leaves the
    parts blank rather than guessing (old Vantage's `_split_address`); the street then holds the whole text, and the
    city-state-zip line is what follows the first comma."""
    raw = ' '.join(str(text or '').split())
    if not raw:
        return '', '', '', '', ''
    rest = raw.partition(',')[2].strip()
    found = _ADDRESS.match(raw)
    if not found:
        return raw, '', '', '', rest
    street, city, state, postcode = (part.strip() for part in found.groups())
    return street, city, state.upper(), postcode, rest


def _iso(day):
    return day.isoformat() if day else ''


def group_facts(deal):
    """{fact: text} about one deal's group, read once per request (plan.md §5.7's table; G.4): rfp prints them on its
    forms, cover and emails (slices 44–46) and the questionnaire prefills from them (slice 42). Keys:
    group.legal_name, dba, address_street, address_city, address_state, zip, city_state_zip, situs_state, sic, fein,
    total_employees, eligible, waiving, atne, enrolled (+ enrolled_estimate, enrolled_source), years_in_business,
    waiting_period, locations, current_carrier, current_funding (the medical incumbent, F144), contact_name,
    contact_first, contact_last, contact_email, contact_title, contact_phone (`deals.contacts.primary`, M30);
    deal.effective_date, deal.anniversary_date (the medical renewal date in force, else the effective date),
    deal.medical_effective_date; broker.agent (`deals.rules.agent_name`), agency, email, phone, address,
    city_state_zip, is_bor (a BOR signed or filed, §5.2). Blank when unknown; never a guess."""
    from deals import contacts as contact_rules
    from deals import rules as deal_rules
    from deals.models import AgencySettings, Contact
    from documents.models import Document
    from intake.models import CurrentCoverage, Intake

    intake = Intake.objects.filter(deal_id=deal.id).first()
    answers = (intake.answers if intake else None) or {}

    def answer(key):
        value = answers.get(key)
        return ', '.join(value) if isinstance(value, list) else str(value or '').strip()

    street, city, state, postcode, city_state_zip = split_address(
        answer('address_physical') or answer('address_mailing')
    )
    medical = incumbent(deal, 'medical') or {}
    coverage = (
        CurrentCoverage.objects.filter(deal_id=deal.id, line='medical', in_force=True)
        .order_by('sort_order', 'id')
        .values('effective_date', 'renewal_date')
        .first()
    ) or {}
    contact = contact_rules.primary(list(Contact.objects.filter(client_id=deal.client_id).order_by('sort_order', 'id')))
    name = (contact.name if contact else '').strip()
    first, _, last = name.partition(' ')
    agency = AgencySettings.get()
    headcount_found = enrolled_headcount(deal)
    bor_filed = Document.objects.filter(deal_id=deal.id, kind='bor').exclude(review_state='wrong').exists()
    return {
        'group.legal_name': answer('legal_name') or deal.client.name,
        'group.dba': answer('dba'),
        'group.address_street': street,
        'group.address_city': city,
        'group.address_state': state,
        'group.zip': postcode,
        'group.city_state_zip': city_state_zip,
        'group.situs_state': answer('situs_state').upper(),
        'group.sic': answer('sic_code'),
        'group.fein': answer('fein'),
        'group.total_employees': answer('total_employees'),
        'group.eligible': answer('employee_count'),
        'group.waiving': answer('waiving_count'),
        'group.atne': answer('atne'),
        'group.enrolled': '' if headcount_found['count'] is None else str(headcount_found['count']),
        'group.enrolled_estimate': bool(headcount_found['estimate']),
        'group.enrolled_source': headcount_found['source'],
        'group.years_in_business': answer('years_in_business'),
        'group.waiting_period': answer('waiting_period'),
        'group.locations': answer('location_count'),
        'group.current_carrier': medical.get('carrier') or '',
        'group.current_funding': medical.get('funding') or '',
        'group.contact_name': name,
        'group.contact_first': first,
        'group.contact_last': last,
        'group.contact_email': contact.email if contact else '',
        'group.contact_title': contact.title if contact else '',
        'group.contact_phone': contact.phone if contact else '',
        'deal.effective_date': _iso(deal.effective_date),
        'deal.anniversary_date': _iso(coverage.get('renewal_date') or deal.effective_date),
        'deal.medical_effective_date': _iso(coverage.get('effective_date')),
        'broker.agent': deal_rules.agent_name(deal, agency),
        'broker.agency': agency.name,
        'broker.email': agency.email,
        'broker.phone': agency.phone,
        'broker.address': agency.address,
        'broker.city_state_zip': agency.city_state_zip,
        'broker.is_bor': bool(intake and intake.bor_signed_at) or bor_filed,
    }
