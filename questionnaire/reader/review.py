"""A staged read against the form as it stands (plan.md §6.8, §10.5; G99, G100, G136; slice 52). Pure.

`entries(view, read, doc)` lists what using the read would change, in the form's order — computed on every look and
again at Use, so the card and the landing never disagree with the form:
- an answer (`ref` the field key) Claude read differently from what the form shows. A read may fill a blank, replace
  the live prefill or an unconfirmed read; an answer a person stands behind — typed, entered for the client, the
  client's (waiting or approved), confirmed or approved — is a listed conflict, never written over (G.6). One Claude
  doubted arrives unticked (§10.5). An equal answer is not listed (D60);
- a row of a repeating section (`ref` "row:<block>:<n>", n its place in the read): it updates the row an earlier read
  of the same file left untouched, else fills the plan row the Advisor started that shares a value with it, else an
  empty row, else adds a row up to the section's maximum (G100: never a row a person or the client touched);
- the answer that opens a section the read has rows for (Florida Blue's Q16 for its conditions), when the read did not
  give it: set so the rows show (the old reader forced the gate). Rows the form's answers would still hide arrive
  unticked and say why.
`counts` says how many of each, and how many rows had no room.
"""

from documents.review_rules import is_approved

from .. import forms, slots, values
from ..engine.conditions import block_visible
from ..engine.spec import block_fields, get_block, section_fields

HELD = {
    'typed': 'Left alone: a person typed this answer on the form.',
    'relay': 'Left alone: this answer was entered for the client.',
    'client': 'Left alone: the client’s answer waits for review.',
    'approved': 'Left alone: a person approved this answer.',
    'confirmed': 'Left alone: a person confirmed this answer.',
    'stored': 'Left alone: this answer is on the form already.',
}
UNSURE_ROW = 'Claude was not sure of {n} of its values. Tick it to use the row; they will be flagged to check.'
OPENS = 'Set so the rows Claude read show on the form.'
HIDDEN = 'The form’s answer to “{label}” hides this section. Tick it to put the row on anyway.'


def same(old, new):
    return str(old if old is not None else '').strip() == str(new if new is not None else '').strip()


def blank(value):
    return not str(value if value is not None else '').strip()


def held(stored, slot, where):
    """Why a slot's answer may not be written over by a read ('' when it may)."""
    if where == 'typed':
        origin = (stored.sources.get(slot) or {}).get('origin')
        return HELD['relay'] if origin == 'relay' else HELD['typed']
    if where == 'client':
        return HELD['client']
    if where != 'stored':
        return ''  # blank, or the live prefill
    source = stored.sources.get(slot) or {}
    if is_approved(source):
        return HELD['approved']
    origin = source.get('origin')
    if origin == 'ai':
        return ''  # an unconfirmed read
    return HELD['confirmed'] if origin == 'prefill' else HELD['client'] if origin == 'client' else HELD['stored']


def _answer(view, key, got):
    field = next(f for f in section_fields(view.form) if f['key'] == key)
    old, where = values.layer(view.stored, view.prefill, key)
    if same(old, got['value']):
        return None
    why = held(view.stored, key, where)
    low = got.get('low') or ''
    return {
        'ref': key,
        'kind': 'answer',
        'slot': key,
        'label': field.get('label') or key,
        'new': got['value'],
        'old': old or '',
        'page': got.get('page'),
        'low': low,
        'sensitive': forms.is_sensitive(view.form['key'], '', key),
        'state': 'conflict' if why else ('fill' if blank(old) else 'replace'),
        'tick': not why and not low,
        'why': why or (f'{low} Tick it to use it.' if low else ''),
    }


def _row_kind(view, block, row, doc):
    """'mine' (only an earlier read of this file wrote it), 'empty', 'prefill' (only the live prefill shows) or
    'taken'."""
    stored = view.stored
    keys = [slots.key(block, row['id'], field['key']) for field in block_fields(view.form, block)]
    if any(slot in stored.client or slot in stored.cleared for slot in keys):
        return 'taken'
    written = [slot for slot in keys if slot in stored.answers]
    if written:
        mine = all(
            (stored.sources.get(slot) or {}).get('origin') == 'ai'
            and (stored.sources.get(slot) or {}).get('doc') == doc
            and not is_approved(stored.sources.get(slot))
            for slot in written
        )
        return 'mine' if mine else 'taken'
    return 'prefill' if any(not blank(view.prefill.get(slot)) for slot in keys) else 'empty'


def _shares(view, block, row, read_row):
    return any(
        not blank(value) and same(view.prefill.get(slots.key(block, row['id'], key)), value)
        for key, value in read_row['values'].items()
    )


def targets(view, block, read_rows, doc):
    """[(row id | None for a new row | False for no room)] for the read's rows, in order; and the earlier read's rows
    this read left over."""
    rows = list(view.stored.rows.get(block) or [])
    kinds = {row['id']: _row_kind(view, block, row, doc) for row in rows}
    mine = [row['id'] for row in rows if kinds[row['id']] == 'mine']
    empty_rows = [row for row in rows if kinds[row['id']] == 'empty']
    started = [row for row in rows if kinds[row['id']] == 'prefill']
    room = get_block(view.form, block)['max_rows'] - len(rows)
    out = []
    for read_row in read_rows:
        if mine:
            out.append(mine.pop(0))
            continue
        match = next((row for row in started if _shares(view, block, row, read_row)), None)
        if match is not None:
            started.remove(match)
            out.append(match['id'])
        elif empty_rows:
            out.append(empty_rows.pop(0)['id'])
        elif room > 0:
            room -= 1
            out.append(None)
        else:
            out.append(False)
    return out, len(mine)


def _row(view, block, number, read_row, target):
    form = view.form
    numbers = {row['id']: n for n, row in enumerate(view.stored.rows.get(block) or [], start=1)}
    changed = []
    for field in block_fields(form, block):
        key = field['key']
        if key not in read_row['values']:
            continue
        old = values.effective(view.stored, view.prefill, slots.key(block, target, key)) if target else ''
        if same(old, read_row['values'][key]):
            continue
        low = key in (read_row.get('low') or [])
        changed.append(
            {
                'key': key,
                'label': field.get('label') or key,
                'new': read_row['values'][key],
                'old': old or '',
                'low': low,
            }
        )
    if not changed:
        return None
    unsure = sum(1 for value in changed if value['low'])
    return {
        'ref': f'row:{block}:{number}',
        'kind': 'row',
        'block': block,
        'block_label': get_block(form, block)['label'],
        'number': number,
        'target': target,
        'target_number': numbers.get(target) if target else None,
        'values': changed,
        'page': read_row.get('page'),
        'low': UNSURE_ROW.format(n=unsure) if unsure else '',
        'sensitive': forms.is_sensitive(form['key'], block, None),
        'state': 'replace' if target and any(not blank(value['old']) for value in changed) else 'fill',
        'tick': not unsure,
        'why': UNSURE_ROW.format(n=unsure) if unsure else '',
    }


def _scalars_after(view, answers):
    scalars = dict(view.view[0])
    scalars.update({entry['slot']: entry['new'] for entry in answers if entry['state'] != 'conflict'})
    return scalars


def _opener(view, block, read, answers, read_rows):
    """The entry that opens `block` for the read's rows, or None (the read gave the answer, or it cannot be set)."""
    gate = get_block(view.form, block).get('visible_if') or {}
    key = gate.get('field')
    if gate.get('op') != 'eq' or not key or key in read['answers'] or any(e['slot'] == key for e in answers):
        return None
    entry = _answer(view, key, {'value': str(gate.get('value', '')), 'page': read_rows[0].get('page'), 'low': ''})
    if entry is None or entry['state'] == 'conflict':
        return None
    return {**entry, 'opens': block, 'why': OPENS}


def entries(view, read, doc):
    """(entries in the form's order, counts {answers, rows, conflicts, ticked, no_room, left_over})."""
    form = view.form
    answers = [entry for key, got in read.get('answers', {}).items() if (entry := _answer(view, key, got))]
    order = {field['key']: n for n, field in enumerate(section_fields(form))}
    rows, no_room, left_over = [], 0, 0
    for block in form.get('blocks') or {}:
        read_rows = (read.get('rows') or {}).get(block) or []
        if not read_rows:
            continue
        opener = _opener(view, block, read, answers, read_rows)
        if opener:
            answers.append(opener)
        hidden = not block_visible(form, block, _scalars_after(view, answers))
        gate_label = next(
            (
                f.get('label')
                for f in section_fields(form)
                if f['key'] == (get_block(form, block).get('visible_if') or {}).get('field')
            ),
            '',
        )
        found, left = targets(view, block, read_rows, doc)
        left_over += left
        for number, (read_row, target) in enumerate(zip(read_rows, found, strict=True), start=1):
            if target is False:
                no_room += 1
                continue
            entry = _row(view, block, number, read_row, target)
            if entry and hidden:
                entry.update(tick=False, why=HIDDEN.format(label=gate_label))
            if entry:
                rows.append(entry)
    answers.sort(key=lambda entry: order.get(entry['slot'], 0))
    listed = answers + rows
    counts = {
        'answers': sum(1 for e in answers if e['state'] != 'conflict'),
        'rows': len(rows),
        'conflicts': sum(1 for e in listed if e['state'] == 'conflict'),
        'ticked': sum(1 for e in listed if e['tick']),
        'no_room': no_room,
        'left_over': left_over,
    }
    return listed, counts
