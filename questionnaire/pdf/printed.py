"""What a filled form prints (plan.md §9.12; G19, G57 B1/B3, G136, OQ85). Pure.

`printed(view, row, client)` reads one `FormView`:
- each slot's effective value without the client's waiting answers: only stored, approved values and the prefill the
  form shows print (OQ85: a client's pending answer never prints until a person approves it);
- hidden answers dropped (`walk.visible_values`, G19);
- every row with its number on our form (1-based, its place in the list), so an attachment names a row the way the
  tab does; `filled(printed, block)` keeps the rows holding an answer, so a blank first row never hides the second
  (B1);
- the signatures, and the officer's print-name box falling back to the signed name when it is blank (B3).

`Printed` is plain data; the exporters and the check read it, never the database.
"""

from collections import namedtuple

from .. import values
from ..engine import walk
from . import fonts

Printed = namedtuple('Printed', 'form scalars rows officer agent client')


def _signer(row, who):
    signed_at = getattr(row, f'{who}_signed_at', None) if row is not None else None
    if signed_at is None:
        return None
    return {'name': getattr(row, f'{who}_name'), 'at': signed_at, 'date': fonts.signed_on(signed_at)}


def _approved_only(stored):
    """The stored JSON with the client's waiting answers left out (OQ85)."""
    return values.Stored(stored.answers, stored.sources, {}, stored.cleared, stored.rows)


def printed(view, row, client=''):
    form = view.form
    shown = values.shown(form, _approved_only(view.stored), view.prefill)
    scalars, by_block = walk.visible_values(form, shown)
    officer = _signer(row, 'officer')
    if officer:
        for field in [f for section in form['sections'] for f in section.get('fields') or []]:
            if field.get('prefill') == 'officer_name' and not str(scalars.get(field['key']) or '').strip():
                scalars = {**scalars, field['key']: officer['name']}
    rows = {block: [(n, vals) for n, (_id, vals) in enumerate(listed, 1)] for block, listed in by_block.items()}
    return Printed(form, scalars, rows, officer, _signer(row, 'agent'), client)


def has_data(vals):
    return any(str(value or '').strip() for value in vals.values())


def filled(found, block):
    """[(number, values)] of a block's rows that hold an answer, in order."""
    return [(number, vals) for number, vals in found.rows.get(block) or [] if has_data(vals)]


def text(vals, key):
    raw = vals.get(key)
    return '' if raw is None else str(raw).strip()
