"""The packet's ticks (plan.md §6.10 `include`; K35, K56). Pure.

`RfpRequest.include` keeps only the ticks that differ from the default, so a row that was never touched keeps
following the carrier picks. A write sends `{key: true | false | null}` (null puts the row back on its default) or
`'reset'` (everything back to the recommendation, K54). A key no card holds any more is ignored on read and pruned on
the next write (K56).
"""

RESET = 'reset'


def resolved(stored, defaults):
    """{key: ticked} for every card: the stored tick, else the default."""
    stored = stored or {}
    return {key: bool(stored.get(key, default)) for key, default in defaults.items()}


def merged(stored, change, defaults):
    """The include map to store after `change` ({key: bool | None} or RESET), against the defaults the request will
    have after this write."""
    if change == RESET:
        return {}
    out = {key: value for key, value in (stored or {}).items() if key in defaults and value != defaults[key]}
    for key, value in change.items():
        if value is None or value == defaults.get(key):
            out.pop(key, None)
        else:
            out[key] = value
    return dict(sorted(out.items()))
