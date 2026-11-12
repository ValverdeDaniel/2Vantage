"""Provider slots: facts deals needs from apps to its right (plan.md §3.3, O.1).

deals never imports a right app. Each slot is one function with a default answer, so deals runs and passes its tests
before the right app exists; the right app fills it in its AppConfig.ready() with `fill(name, fn)`. Only deals'
services and payloads call a provider; its pure rules take the fact as an argument.

- `client_has_sold(client_id) -> bool`, filled by quotes: whether any plan on any of the client's deals is sold.
  The status door asks it before Back to prospect, and before letting the deals' `opened_as` follow (§5.1).
"""


def _no_plan_is_sold(client_id):
    return False  # true while no app can sell a plan


_slots = {'client_has_sold': _no_plan_is_sold}
DEFAULTS = dict(_slots)


def fill(name, fn):
    """Called by the right app in AppConfig.ready()."""
    if name not in _slots:
        raise KeyError(f'deals has no provider slot named {name}')
    _slots[name] = fn


def client_has_sold(client_id):
    return bool(_slots['client_has_sold'](client_id))
