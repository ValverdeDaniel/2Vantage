"""Asking more on a request the client already has (plan.md §5.8; L51, L53, L58; old 891f1b3
`client_request.extend_ask`). Pure: a request's asks (plan.md §6.12's shape) and the refs to add.

`join(asks, refs)` → (asks with the refs added, [refs it added]): an intake question goes into `intake.keys` (a request
asking nothing of the intake starts a `selected` ask), a part of the intake into `intake.blocks`, a census value into
`census.cells` (a request asking no census starts a `selected` one), their census file sets `census.file`, a file into
`documents.slots`, and (slice 58) a questionnaire answer `q:<form>:<slot>` into its form's picks online (a row's
answer picks its table, a question itself) while a whole form online `qform:<form>` asks the form whole, dropping its
picks. A ref the asks already name explicitly is not added twice; what a scope carries the caller leaves
out (it knows what is missing now, `portal.asked`). Questions keep the form's order. More than `asks.CELL_LIMIT`
census values on one request is refused (`TooMany`): their census file is the better ask (L46).
"""

import copy

from intake import form as intake_form

from .asks import CELL_LIMIT, empty, no_census, no_documents


class TooMany(ValueError):
    """More census values than one request may name."""


def _intake(out):
    if not out.get('intake'):
        out['intake'] = {'scope': 'selected', 'keys': [], 'blocks': []}
    out['intake'].setdefault('keys', [])
    out['intake'].setdefault('blocks', [])
    return out['intake']


def _census(out):
    census = out.get('census') or no_census()
    census.setdefault('cells', [])
    out['census'] = census
    return census


def _add_cell(out, member, column):
    census = _census(out)
    cell = [int(member), column]
    if cell in census['cells']:
        return False
    census['cells'].append(cell)
    if census.get('scope', 'none') == 'none':
        census['scope'] = 'selected'
    return True


def _append(items, item):
    if item in items:
        return False
    items.append(item)
    return True


def _add(out, ref):
    area, _, rest = ref.partition(':')
    if area == 'intake' and rest.startswith('block:'):
        return _append(_intake(out)['blocks'], rest.removeprefix('block:'))
    if area == 'intake':
        intake = _intake(out)
        if rest in intake['keys']:
            return False
        order = {key: at for at, key in enumerate(intake_form.KEYS)}
        intake['keys'] = sorted([*intake['keys'], rest], key=lambda key: order.get(key, len(order)))
        return True
    if ref == 'census:file':
        census = _census(out)
        if census.get('file'):
            return False
        census['file'] = True
        return True
    if area == 'census':
        member, _, column = rest.partition(':')
        return _add_cell(out, member, column)
    if area == 'doc':
        documents = out.get('documents') or no_documents()
        out['documents'] = documents
        return _append(documents.setdefault('slots', []), rest)
    if area in ('q', 'qform'):
        return _add_form(out, area, rest)
    return False


def _add_form(out, area, rest):
    """A questionnaire answer joins its form's picks online; a whole form joins whole (G80)."""
    form_key, _, slot = rest.partition(':')
    asked = out.setdefault('questionnaires', [])
    entry = next((one for one in asked if one['form'] == form_key), None)
    if area == 'qform':
        if entry is None:
            asked.append({'form': form_key, 'mode': 'online', 'picks': {'fields': [], 'blocks': []}})
            return True
        whole = entry['mode'] == 'online' and not (entry['picks']['fields'] or entry['picks']['blocks'])
        entry.update(mode='online', picks={'fields': [], 'blocks': []})
        return not whole
    block, _dot, rest_of = slot.partition('.')
    kind, key = ('blocks', block) if rest_of else ('fields', block)
    if entry is None:
        asked.append({'form': form_key, 'mode': 'online', 'picks': {'fields': [], 'blocks': [], kind: [key]}})
        return True
    picks = entry.setdefault('picks', {'fields': [], 'blocks': []})
    if entry['mode'] == 'online' and not (picks.get('fields') or picks.get('blocks')):
        return False  # the whole form is asked online already
    entry['mode'] = 'online'
    return _append(picks.setdefault(kind, []), key)


def join(asks, refs):
    """(new asks, [refs added]); raises TooMany past the census limit. `asks` is never changed in place."""
    out = copy.deepcopy(asks) if asks else empty()
    added = [ref for ref in dict.fromkeys(refs) if _add(out, ref)]
    if len((out.get('census') or {}).get('cells') or []) > CELL_LIMIT:
        raise TooMany()
    return out, added
