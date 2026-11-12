"""Provider slots: facts census needs from apps to its right (plan.md §5.3.3, O.1).

census never imports a right app. Each slot is one function with a default answer, filled by the right app in its
AppConfig.ready() with `fill(name, fn)`; only census's services and payloads call it.

- `carrier_required(deal_id) -> {key: {employee: [carrier], dependent: [carrier]}}`, filled by rfp (slice 45): the
  columns the census files the deal's RFP will send require (K124). Until then it answers {}. A pick that changes it
  refreshes the stored counts on commit (`census.facts.refresh`, K.6).
"""


def _nothing_required(deal_id):
    return {}


_slots = {'carrier_required': _nothing_required}
DEFAULTS = dict(_slots)


def fill(name, fn):
    if name not in _slots:
        raise KeyError(f'census has no provider slot named {name}')
    _slots[name] = fn


def carrier_required(deal_id):
    return _slots['carrier_required'](deal_id)
