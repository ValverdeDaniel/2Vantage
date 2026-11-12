"""Provider slots: facts quotes needs from apps to its right (plan.md §3.3, O.1, O.6 #47).

quotes never imports a right app. Each slot is one function with a default answer, so quotes runs and passes its
tests before the right app exists; the right app fills it in its AppConfig.ready() with `fill(name, fn)`. Only quotes'
services, payloads and files call a provider.

- `disclosure_state(deal_id) -> 'signed' | 'started' | 'not_started'`, filled by questionnaire (slice 43): the SIIA
  stop-loss disclosure's state, which the stop-loss workbook's Binding Notes print (G117; slice 36) in the words of
  `DISCLOSURE_WORDS`, old Vantage's own (891f1b3 `pipeline/workbooks._sl_binding_rows`).
"""

SIGNED, STARTED, NOT_STARTED = 'signed', 'started', 'not_started'
DISCLOSURE_WORDS = {
    SIGNED: 'SIIA disclosure signed',
    STARTED: 'SIIA disclosure started, not signed',
    NOT_STARTED: 'SIIA disclosure not started',
}


def _no_disclosure(deal_id):
    return NOT_STARTED  # true while no app holds a disclosure


_slots = {'disclosure_state': _no_disclosure}
DEFAULTS = dict(_slots)


def fill(name, fn):
    """Called by the right app in AppConfig.ready()."""
    if name not in _slots:
        raise KeyError(f'quotes has no provider slot named {name}')
    _slots[name] = fn


def disclosure_state(deal_id):
    return _slots['disclosure_state'](deal_id)
