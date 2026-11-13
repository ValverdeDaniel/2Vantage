"""The Ask card's plan: what an open request asks once a person's ticks are applied (plan.md §5.8, §7.13 `POST
review/requests/{rid}/form/`; L42, L59, L36; old 891f1b3 `review/link_form.py`, `client_request.shrink`/`widen`). Pure:
the request's asks (plan.md §6.12's shape), the change, and what the link carries now.

`parse(data)` reads the body's form part into a `Change` (400 by field); `plan(asks, change, carried=, columns=)` →
`Planned(asks, added, removed, refused, changed)`, in the order the write applies it (L42): removals first (whole
parts, then items, then census columns), then what is switched on (a part's scope, census columns, the census file,
the checklist's missing files, the intake's parts), then what the drafts add (`rules.join`). The level and each
person's settings follow in the service.

A removal takes off what the client is asked, never what they said (L59). An item asked only because a scope
carries it ("the whole intake", "every blank", "whatever is missing") cannot come off alone: it is `refused` by ref,
and the service names it ("switch the intake to picked questions, or take the intake off"). `carried` is every ref
the link asks now (`portal.asked.carried`), so an item no scope carries comes off quietly. `columns` is the census
columns the portal asks, for taking one column off a scope that asked them all.
"""

import copy
from collections import namedtuple

from census import fields as census_fields

from . import join as join_rules
from .asks import CENSUS_SCOPES, INTAKE_BLOCKS, INTAKE_SCOPES, empty, no_census, no_documents

PARTS = ('intake', 'census', 'documents')
ON_INTAKE = tuple(scope for scope in INTAKE_SCOPES if scope != 'selected')
ON_CENSUS = tuple(scope for scope in CENSUS_SCOPES if scope not in ('none', 'selected'))

Change = namedtuple(
    'Change', 'off_refs off_columns off_parts on_intake on_census on_columns on_file on_missing on_blocks'
)
Planned = namedtuple('Planned', 'asks added removed refused changed')


def nothing():
    return Change((), (), (), '', '', (), None, None, ())


def _strings(raw, field, errors):
    if raw in (None, ''):
        return ()
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        errors[field] = ['Send a list of keys.']
        return ()
    return tuple(dict.fromkeys(item.strip() for item in raw if item.strip()))


def _flag(raw, field, errors):
    if raw in (None, True, False):
        return raw
    errors[field] = [f'{field} must be true or false.']
    return None


def _scope(raw, allowed, field, errors):
    scope = str(raw or '')
    if scope and scope not in allowed:
        errors[field] = [f'Name the scope as one of: {", ".join(allowed)}.']
        return ''
    return scope


def parse(data):
    """(Change, {field: [sentence]}) from the body's `off` and `on`."""
    errors = {}
    off = data.get('off') or {}
    on = data.get('on') or {}
    if not isinstance(off, dict) or not isinstance(on, dict):
        return nothing(), {'off': ['Send off and on as objects.']}
    parts = _strings(off.get('parts'), 'off.parts', errors)
    if bad := [part for part in parts if part not in PARTS]:
        errors['off.parts'] = [f'Not a part of the form: {", ".join(bad)}.']
    columns = _strings(off.get('columns'), 'off.columns', errors)
    on_columns = _strings(on.get('columns'), 'on.columns', errors)
    if bad := [key for key in (*columns, *on_columns) if key not in census_fields.BY_KEY]:
        errors['columns'] = [f'Not a census column: {", ".join(bad)}.']
    blocks = _strings(on.get('blocks'), 'on.blocks', errors)
    if bad := [block for block in blocks if block not in INTAKE_BLOCKS]:
        errors['on.blocks'] = [f'Not a part of the intake: {", ".join(bad)}.']
    change = Change(
        off_refs=_strings(off.get('refs'), 'off.refs', errors),
        off_columns=columns,
        off_parts=parts,
        on_intake=_scope(on.get('intake'), ON_INTAKE, 'on.intake', errors),
        on_census=_scope(on.get('census'), ON_CENSUS, 'on.census', errors),
        on_columns=on_columns,
        on_file=_flag(on.get('census_file'), 'on.census_file', errors),
        on_missing=_flag(on.get('documents_missing'), 'on.documents_missing', errors),
        on_blocks=blocks,
    )
    return change, errors


def touches(change):
    """True when the change says anything about the form (a settings-only body leaves what a link asks alone)."""
    return change != nothing()


# ---- removals ----------------------------------------------------------------------------------------------------


def _tidy(out):
    """A part left asking nothing goes: picked questions with none left, picked census values with none left."""
    intake = out.get('intake')
    if intake and intake.get('scope') == 'selected' and not intake.get('keys'):
        intake['scope'] = ''
    if intake and not intake.get('scope') and not intake.get('keys') and not intake.get('blocks'):
        out['intake'] = None
    census = out.get('census') or no_census()
    if census.get('scope') == 'selected' and not census.get('cells'):
        census['scope'] = 'none'
    if census.get('scope') == 'none':
        census['columns'] = []
    out['census'] = census


def _part_off(out, part):
    if part == 'intake':
        out['intake'] = None
    elif part == 'census':
        out['census'] = no_census()
    else:
        out['documents'] = no_documents()


def _ref_off(out, ref, carried):
    """True when the ref is off (taken off, or never asked); False when only a scope carries it."""
    area, _, rest = ref.partition(':')
    intake = out.get('intake') or {}
    census = out.get('census') or no_census()
    documents = out.get('documents') or no_documents()
    if area == 'intake' and rest.startswith('block:'):
        block = rest.removeprefix('block:')
        if block in (intake.get('blocks') or []):
            intake['blocks'] = [b for b in intake['blocks'] if b != block]
        return True
    if area == 'intake':
        if rest in (intake.get('keys') or []):
            intake['keys'] = [key for key in intake['keys'] if key != rest]
            return ref not in carried or intake.get('scope') in ('', 'selected')
        return ref not in carried
    if ref == 'census:file':
        census['file'] = False
        return True
    if area == 'census':
        member, _, column = rest.partition(':')
        cells = census.get('cells') or []
        kept = [cell for cell in cells if not (str(cell[0]) == member and cell[1] == column)]
        census['cells'] = kept
        if len(kept) < len(cells):
            return ref not in carried or census.get('scope') in ('none', 'selected')
        return ref not in carried
    if area == 'doc':
        if rest in (documents.get('slots') or []):
            documents['slots'] = [slot for slot in documents['slots'] if slot != rest]
            return ref not in carried or not documents.get('missing')
        return ref not in carried
    if area in ('q', 'qform'):
        return _form_off(out, area, rest, ref, carried)
    return ref not in carried


def _form_off(out, area, rest, ref, carried):
    """A whole form comes off the request; one picked question (or table) comes off its picks — the form goes once
    nothing is picked. A question the whole form carries is refused by name, like a scope's (L59; slice 58)."""
    form_key, _, slot = rest.partition(':')
    forms = out.get('questionnaires') or []
    entry = next((one for one in forms if one['form'] == form_key), None)
    if entry is None:
        return ref not in carried
    if area == 'qform':
        out['questionnaires'] = [one for one in forms if one['form'] != form_key]
        return True
    picks = entry.get('picks') or {}
    key = slot.split('.')[0]
    named = [*(picks.get('fields') or []), *(picks.get('blocks') or [])]
    if key not in named:
        return ref not in carried
    entry['picks'] = {kind: [one for one in picks.get(kind) or [] if one != key] for kind in ('fields', 'blocks')}
    if not (entry['picks']['fields'] or entry['picks']['blocks']):
        out['questionnaires'] = [one for one in forms if one['form'] != form_key]
    return True


def _column_off(out, column, columns):
    census = out.get('census') or no_census()
    census['cells'] = [cell for cell in census.get('cells') or [] if cell[1] != column]
    if census.get('scope') in ON_CENSUS:
        named = census.get('columns') or [key for key in columns if key in census_fields.BY_KEY]
        census['columns'] = [key for key in named if key != column]
        if not census['columns']:
            census['scope'] = 'selected' if census['cells'] else 'none'
    out['census'] = census


# ---- what is switched on -----------------------------------------------------------------------------------------


def _intake_on(out, scope, blocks):
    intake = out.get('intake') or {'scope': '', 'keys': [], 'blocks': []}
    if scope:
        intake['scope'] = scope
        if scope == 'all':
            intake['keys'] = []
    for block in blocks:
        if block not in intake.setdefault('blocks', []):
            intake['blocks'].append(block)
    intake.setdefault('keys', [])
    out['intake'] = intake


def _census_on(out, scope, columns):
    census = out.get('census') or no_census()
    current = census.get('scope', 'none')
    if scope:
        if current in ('none', 'selected'):
            census['columns'] = list(columns)
        census['scope'] = scope
    elif columns:
        if current in ('none', 'selected'):
            census['scope'], census['columns'] = 'blank', list(columns)
        elif census.get('columns'):
            census['columns'] = list(dict.fromkeys([*census['columns'], *columns]))
    if census.get('scope') == 'all':
        census['cells'] = []
    out['census'] = census


def _shaped(asks):
    out = {**empty(), **copy.deepcopy(asks or {})}
    out['census'] = out.get('census') or no_census()
    out['documents'] = out.get('documents') or no_documents()
    out['questionnaires'] = out.get('questionnaires') or []
    return out


def plan(asks, change, *, add=(), carried=frozenset(), columns=()):
    """Planned(asks, [refs added], [refs taken off], [refs refused], changed). Raises join.TooMany past the census
    limit. `asks` is never changed in place."""
    out = _shaped(asks)
    before = _shaped(asks)
    for part in change.off_parts:
        _part_off(out, part)
    removed, refused = [], []
    for ref in change.off_refs:
        if _ref_off(out, ref, carried):
            if ref in carried:
                removed.append(ref)
        else:
            refused.append(ref)
    for column in change.off_columns:
        _column_off(out, column, columns)
    _tidy(out)
    if change.on_intake or change.on_blocks:
        _intake_on(out, change.on_intake, change.on_blocks)
    if change.on_census or change.on_columns:
        _census_on(out, change.on_census, change.on_columns)
    if change.on_file is not None:
        out['census']['file'] = change.on_file
    if change.on_missing is not None:
        out['documents']['missing'] = change.on_missing
    out, added = join_rules.join(out, list(add))
    _tidy(out)
    return Planned(out, added, removed, refused, out != before)
