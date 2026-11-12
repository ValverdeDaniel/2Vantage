"""Quotes' locate hooks (plan.md §10.7; E81, E83, D95; the old benefits/ai/source_check.py `query_for`).

Registered with ai in QuotesConfig.ready(): `queries` names the plan values that came from a file (their source's
`doc`) and how each is looked for; `save` stores each answer as the value's `loc` (deals.values.set_loc), locking the
Deal, then the plans by id. A value typed over a read one keeps its file (E66) and is checked as it now stands.

How a value is asked about is where the reader's own rules live, as the old check had them: the member's coinsurance
is recorded as 100 minus the plan's share, "No charge" as 0, design dollars whole; a worded field the reader may
shorten (a network, a plan type) is never called absent, only weak; a yes/no, a summary the reader wrote and a choice
have no printed form to find, except a choice's own label ("Fully insured").
"""

from django.db import transaction

from deals.values import set_loc
from documents.locate import NOCHECK, VERSION, Located, Query
from documents.locate.fold import as_number, canonical

from . import fields, flags
from .models import Plan
from .services import locks

COMPLEMENT_KEYS = ('coinsurance', 'coinsurance_oon')
NO_CHARGE_WORDS = ('no charge', 'no cost', 'no copay', 'covered in full')
CODE_KEYS = ('sbc_url',)
SUMMARY_KEYS = ('benefit_summary', 'plan_notes')  # written by the reader, not copied: nothing printed to find
# Money copied exactly, cents included; other amounts are a plan's design, recorded whole (within $1).
EXACT_PREFIXES = ('rate_', 'contrib_', 'sl_', 'lf_', 'tpa_', 'unit_rate', 'group_premium')
# Words a carrier prints on a value's row that the field's own label may not use: they pin a common figure (20, $25).
ROW_WORDS = {
    'pcp_copay': 'primary office pcp',
    'specialist_copay': 'specialist',
    'urgent_care_copay': 'urgent',
    'er_copay': 'emergency',
    'coinsurance': 'coinsurance coins',
    'coinsurance_oon': 'coinsurance coins',
    'rx_t1': 'generic tier',
    'rx_t2': 'preferred brand tier',
    'rx_t3': 'non-preferred brand tier',
    'rx_t4': 'specialty tier',
    'rx_deductible': 'deductible pharmacy',
    'den_preventive': 'preventive diagnostic',
    'den_basic': 'basic',
    'den_major': 'major',
    'den_ortho': 'ortho orthodontia',
    'vis_exam_copay': 'exam',
    'vis_materials_copay': 'materials lenses',
    'dis_benefit_pct': 'benefit percentage',
}
AREAS = ['advisor']  # what a browser refetches after the answers land (the comparison's cells)


def _figure(number):
    text = f'{number:.4f}'.rstrip('0').rstrip('.')
    whole, _, fraction = text.partition('.')
    return canonical(whole, fraction)


def _choice_label(field, value):
    return next((choice['label'] for choice in field['choices'] if choice['key'] == value), value)


def query_for(plan, key, value, entry):
    """The Query for one plan value, or a Located NOCHECK when it has no printed form to find."""
    field = fields.BY_KEY.get(key)
    kind = field['type'] if field else 'text'
    if kind == 'yesno':
        return Located(NOCHECK, why='choice')
    if key in SUMMARY_KEYS:
        return Located(NOCHECK, why='summary')
    label = field['label'] if field else ''
    words = (label, ROW_WORDS.get(key, ''), plan.name)
    where = {'page': entry.get('page'), 'anchors': words, 'hint': f'{plan.carrier} {plan.name}'}
    if key in CODE_KEYS:
        return Query(value, kind='code', **where)
    if kind == 'choice':
        value = _choice_label(field, value)
    figure = as_number(value)
    snippet = entry.get('line') or ''
    if figure is None:
        return Query(value, strict=False, snippet=snippet, **where)
    number = float(figure)
    alternatives, wordings, tolerance = [], [], 0.0
    if key in COMPLEMENT_KEYS and 0 <= number <= 100:
        alternatives.append((_figure(100 - number), 'complement'))
    if kind in ('amount', 'rate') and number == 0:
        wordings.extend((wording, 'no_charge') for wording in NO_CHARGE_WORDS)
    if kind == 'amount' and not key.startswith(EXACT_PREFIXES):
        tolerance = 1.0
    if kind == 'number' and '.' in figure and number < 10:
        alternatives.append((_figure(round(number * 100, 4)), 'percent'))  # a corridor 1.25 printed 125%
    return Query(
        value,
        alternatives=tuple(alternatives),
        wordings=tuple(wordings),
        tolerance=tolerance,
        snippet=snippet,
        **where,
    )


def _checked(entry):
    loc = entry.get('loc')
    return isinstance(loc, dict) and loc.get('v') == VERSION


def queries(deal, document, recheck):
    """[((plan id, key, value), Query or Located)] for the live plans' values that name `document`."""
    items = []
    plans = Plan.objects.filter(deal=deal).only('id', 'carrier', 'name', 'line', 'values', 'sources').order_by('id')
    for plan in plans:
        for key, entry in plan.sources.items():
            value = plan.values.get(key)
            if not isinstance(entry, dict) or entry.get('doc') != document.id or value in (None, ''):
                continue
            if recheck or not _checked(entry):
                items.append(((plan.id, key, value), query_for(plan, key, value, entry)))
    return items


@transaction.atomic
def save(user, deal, document, answers):
    """Store each answer as its value's `loc`, unless the value changed meanwhile. {'saved': n, 'areas': [...]}."""
    by_plan = {}
    for (plan_id, key, value), loc in answers:
        by_plan.setdefault(plan_id, []).append((key, value, loc))
    locks.deal(deal.id)
    rows = list(Plan.objects.select_for_update().filter(deal=deal, id__in=by_plan).order_by('id'))
    changed, saved = [], 0
    for plan in rows:
        stored = sum(
            set_loc(plan.values, plan.sources, key, value, document.id, loc) for key, value, loc in by_plan[plan.id]
        )
        if stored:
            saved += stored
            changed.append(plan)
    if changed:
        for plan in changed:
            flags.stamp(plan)  # a value the file does not print may now be an open warning (OQ28)
        Plan.objects.bulk_update(changed, ['sources', 'flags'])  # bookkeeping: `updated_at` stays (§3.7)
    return {'saved': saved, 'areas': AREAS if saved else []}
