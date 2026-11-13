"""What an Activity row's `changes` hold (plan.md §3.7, §3.8, O.3.2), built, cleaned and merged; pure, no queries.

Before and after per key and target: [{"t": "plan:41", "k": {"rate_ee": ["612.50", "640"]}}]; a key-only row (census
rows, sensitive questionnaire slots, lasers) keeps the keys alone: {"t": ..., "k": ["dob"]}. Activity's writer
(activity.py) is the one caller that stores them, and re-exports these names (`activity.change`, …).
"""

# Value keys whose values never enter Activity, only their keys (§3.8, rule 4: lasers): filled by the owning app in
# AppConfig.ready() (quotes: `sl_lasers`, slice 36). A diff that holds one keeps its other keys' before and after, and
# the hidden key rides beside them as a key-only entry, so the row cannot be reverted (KEYS_ONLY).
key_only_values = set()


def change(target, diff):
    """One `changes` entry from a {key: [before, after]} diff (as values.apply returns it)."""
    return {'t': target, 'k': diff}


def _clean(changes, keys_only):
    out = []
    for entry in changes or []:
        keys, hidden = entry['k'], []
        if isinstance(keys, dict):
            keys = {key: list(pair) for key, pair in keys.items() if pair[0] != pair[1]}
            hidden = sorted(key for key in keys if key in key_only_values)
            keys = {key: pair for key, pair in keys.items() if key not in key_only_values}
        if keys_only or isinstance(keys, list):
            keys = sorted(set(keys))
        if keys:
            out.append({'t': str(entry['t']), 'k': keys})
        if hidden:
            out.append({'t': str(entry['t']), 'k': hidden})
    return out


def merge(first, then):
    """Two change lists as one: each key keeps its first "before" and last "after"; a key back where it began goes."""
    merged, order = {}, []
    for entry in [*first, *then]:
        target, keys = entry['t'], entry['k']
        if target not in merged:
            merged[target] = list(keys) if isinstance(keys, list) else {k: list(v) for k, v in keys.items()}
            order.append(target)
        elif isinstance(merged[target], list) or isinstance(keys, list):
            merged[target] = sorted(set(merged[target]) | set(keys))
        else:
            for key, (before, after) in keys.items():
                merged[target][key] = [merged[target][key][0] if key in merged[target] else before, after]
    return _clean([{'t': t, 'k': merged[t]} for t in order], keys_only=False)


def holds_keys_only(changes):
    return any(isinstance(entry['k'], list) for entry in changes)
