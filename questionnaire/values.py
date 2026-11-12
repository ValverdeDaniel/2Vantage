"""One answer per slot on every surface (plan.md §6.8; G27, G33, G136). Pure.

`effective(stored, prefill, slot)` is the one rule, read by the display, progress, the checks, the PDF and the
portal's to-do:
1. a staff-typed or relayed answer (`answers` with a `typed` or `relay` source);
2. else the client's waiting answer (`client`, status `pending`): violet "From the client";
3. else the stored value (an approved client answer, a read, or a frozen prefill);
4. else the live prefill, unless a person cleared the slot (`cleared`);
5. else blank.

`Stored` is a questionnaire's JSON as stored, or the empty shape of a form nobody has written yet (`stored_of(None,
rows)`), so a GET never needs a row (G26). `shown(...)` turns it into the engine's view, and `statuses(...)` gives each
slot on screen its state: missing, prefill, client or to_check (blank and ok slots are left out).
"""

from collections import namedtuple

from documents.review_rules import open_warning

from . import slots
from .engine import walk

Stored = namedtuple('Stored', 'answers sources client cleared rows')
STAFF = ('typed', 'relay')


def stored_of(row, starting_rows):
    """The questionnaire's stored JSON, or the empty shape with the starting rows when there is no row yet."""
    if row is None:
        return Stored({}, {}, {}, [], starting_rows)
    return Stored(row.answers or {}, row.sources or {}, row.client or {}, list(row.cleared or []), row.rows or {})


def _waiting(stored, slot):
    entry = stored.client.get(slot)
    if isinstance(entry, dict) and entry.get('status') == 'pending':
        return entry.get('value', '') if 'value' in entry else stored.answers.get(slot, '')
    return None


def layer(stored, prefill, slot):
    """(value, where) for one slot; `where` is typed, client, stored, prefill or ''."""
    if slot in stored.answers and (stored.sources.get(slot) or {}).get('origin') in STAFF:
        return stored.answers[slot], 'typed'
    waiting = _waiting(stored, slot)
    if waiting is not None:
        return waiting, 'client'
    if slot in stored.answers:
        return stored.answers[slot], 'stored'
    if slot not in stored.cleared and prefill.get(slot) not in (None, ''):
        return prefill[slot], 'prefill'
    return '', ''


def effective(stored, prefill, slot):
    return layer(stored, prefill, slot)[0]


def shown(form, stored, prefill):
    """The engine's view (scalars, {block: [(row id, {field: value})]}) of every slot's effective value."""
    from .engine.spec import block_fields, section_fields

    scalars = {}
    for field in section_fields(form):
        value = effective(stored, prefill, field['key'])
        if value not in (None, ''):
            scalars[field['key']] = value
    rows = {}
    for block_key in (form.get('blocks') or {}).keys():
        out = []
        for row in stored.rows.get(block_key) or []:
            values = {}
            for field in block_fields(form, block_key):
                value = effective(stored, prefill, slots.key(block_key, row['id'], field['key']))
                if value not in (None, ''):
                    values[field['key']] = value
            out.append((row['id'], values))
        rows[block_key] = out
    return scalars, rows


def statuses(form, stored, prefill, view):
    """{slot: missing | prefill | client | to_check} for the slots on screen; blank and ok slots are left out."""
    out = {}
    for entry in walk.order(form, view):
        slot = entry['slot']
        value, where = layer(stored, prefill, slot)
        if value in (None, '') or not str(value).strip():
            if entry['required']:
                out[slot] = 'missing'
        elif where == 'client':
            out[slot] = 'client'
        elif where == 'prefill':
            out[slot] = 'prefill'
        elif open_warning(stored.sources.get(slot)):
            out[slot] = 'to_check'
    return out


def flags(form, stored, prefill):
    """The open warnings on the slots on screen: the stored count `Questionnaire.flags` (O.3.7)."""
    view = shown(form, stored, prefill)
    return sum(1 for state in statuses(form, stored, prefill, view).values() if state == 'to_check')
