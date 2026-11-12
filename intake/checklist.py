"""The marketing checklist (plan.md §5.2, §6.5; B25–B28, O.6 #2). Pure.

Slice 41 brings the first item, the COBRA tick, because the Census tab shows it (C25): "Did anybody check for COBRA
participants?" lives where the answer lives, and the checklist row reads the same entry (the old `cobra`
MarketingAttestation, 891f1b3 `CobraCheck.jsx`). Slice 40 adds the other items, the size tier, the card and the
requirement controls (Not needed, Still needed ▸) to this module.

`Intake.checklist` holds one entry per item a person touched: `{checked, by, at, note, requirement, client_note,
form_key}` (§6.5); an item never touched has no entry and reads unchecked.
"""

COBRA = 'cobra'
ATTESTED = (COBRA,)  # items a person ticks; slice 40 adds salary & occupation and the document items
LABELS = {COBRA: 'COBRA participants'}
REQUIREMENTS = ('', 'required', 'waived')  # '' = the item's own rule; 'waived' reads "Marked not needed"


def entry_of(checklist, key):
    """The stored entry of one item, or {}."""
    found = (checklist or {}).get(key)
    return dict(found) if isinstance(found, dict) else {}


def ticked(entry, checked, user_id, at):
    """The entry after a person ticks (or unticks) it, or None when nothing changes. Who and when follow the tick;
    the requirement and notes stay."""
    if bool(entry.get('checked')) == bool(checked):
        return None
    after = {key: value for key, value in entry.items() if key not in ('checked', 'by', 'at')}
    if checked:
        after.update({'checked': True, 'by': user_id, 'at': at})
    return after


def item_state(key, entry, by_name=''):
    """One item as a screen shows it: {key, label, checked, by, by_name, at, requirement}."""
    return {
        'key': key,
        'label': LABELS[key],
        'checked': bool(entry.get('checked')),
        'by': entry.get('by'),
        'by_name': by_name if entry.get('checked') else '',
        'at': entry.get('at') if entry.get('checked') else None,
        'requirement': entry.get('requirement') or '',
    }
