"""The finder's index (plan.md §7.8 `plans/find/`; F14, F15, OQ14): what the Advisor's finder searches on every plan of
a deal, every line at once, in one query, so "Also matches 2 on Dental" needs no second read.

Each live plan gives its name, plan number, carrier, network, plan type and codes as texts, and `carrier`, the
registry key its carrier name means (`deals.carriers.match`, the one matcher; None for a carrier it does not know).
The browser's pure `finder` matches the typed words against these texts and folds a carrier's aliases through
`carrier`, with the aliases `/api/meta/` serves ("UHC" finds UnitedHealthcare). Current plans are listed, marked
`current`, because the finder never counts them as hits but the index serves Claude's board tools too (slice 24).
"""

from django.db.models.fields.json import KeyTextTransform

from deals import carriers

from ..models import Plan


def _codes(raw):
    """Plan.codes as texts: a code may be a text or a {kind: code} record (F143)."""
    out = []
    for item in raw if isinstance(raw, list) else []:
        values = item.values() if isinstance(item, dict) else [item]
        out.extend(str(value) for value in values if isinstance(value, (str, int)) and str(value).strip())
    return out


def find_index(deal):
    """[{id, line, current, carrier, texts}] for the deal's live plans, in line and plan order."""
    rows = (
        Plan.objects.filter(deal=deal)
        .annotate(network=KeyTextTransform('network', 'values'), plan_type=KeyTextTransform('plan_type', 'values'))
        .order_by('line', 'sort_order', 'id')
        .values_list('id', 'line', 'role', 'carrier', 'name', 'plan_number', 'network', 'plan_type', 'codes')
    )
    keys = {}
    out = []
    for pid, line, role, carrier, name, number, network, plan_type, codes in rows:
        if carrier not in keys:
            keys[carrier] = carriers.match(carrier)
        texts = [text for text in (name, number, carrier, network, plan_type, *_codes(codes)) if text]
        out.append({'id': pid, 'line': line, 'current': role == 'current', 'carrier': keys[carrier], 'texts': texts})
    return out
