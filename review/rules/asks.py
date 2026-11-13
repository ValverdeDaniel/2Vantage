"""What a request asks (plan.md §6.12 `ClientRequest.asks`; L55–L59). Pure: vocabularies only, no database.

`clean(raw)` checks a request's asks against the shape and the vocabularies and returns (asks, errors): every part
present in the stored shape, keys in their vocabulary, nothing asked twice. Census cells name member ids; the services
check those belong to the deal. `sections(asks)` is the sections a request carries (`intake`, `census`,
`questionnaire`), which a section's own board will list (L45; D-203). How a card names an ask is `ask_words`.

Scopes: intake `selected` (the keys), `missing` (every shown blank), `required` (what marketing needs and does not
have), `all` (the whole form); census `none`, `selected` (the cells), `blank` (every empty cell), `missing` (the
required blanks), `all` (the whole census), each narrowed to `columns` when they are given; `missing` and `required`
are worked out on read, so a link asks what is still missing (L6 Ch. 2). Intake `keys` and census `cells` named beside
another scope are asked too: what the tray joins onto an open request (slice 56, `rules.join`) rides beside its scope.
"""

from census import fields as census_fields
from deals import lines
from intake import form as intake_form
from questionnaire import forms as questionnaire_forms

INTAKE_SCOPES = ('selected', 'missing', 'required', 'all')
INTAKE_BLOCKS = ('contacts', 'coverage', 'lines', 'bor', 'files')
CENSUS_SCOPES = ('none', 'selected', 'blank', 'missing', 'all')
FORM_MODES = ('online', 'upload')
# The files a client is asked for (old REQUESTABLE_DOC_TYPES and the compliance uploads): never an SBC, a quote or a
# proposal (D-183); the census file is its own ask. A renewal or an invoice may name its line: `invoice@medical`.
DOCUMENT_KINDS = (
    'renewal',
    'invoice',
    'claims',
    'questionnaire',
    'stop_loss',
    'bor',
    'carrier_auth',
    'plan_doc',
    'form_5500',
    'other',
)
LINE_KINDS = ('renewal', 'invoice')
CELL_LIMIT = 500  # census cells one request names; more is a census file to ask for (L46)


def no_census():
    return {'scope': 'none', 'columns': [], 'cells': [], 'file': False}


def no_documents():
    return {'slots': [], 'missing': False}


def empty():
    """Asks that ask nothing, in the stored shape."""
    return {'intake': None, 'census': no_census(), 'questionnaires': [], 'documents': no_documents()}


NOTHING = 'Pick something to ask for.'


def _strings(value, field, errors):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors[field] = ['Send a list of keys.']
        return []
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


def _unknown(keys, known):
    return sorted(set(keys) - set(known))


def _clean_intake(raw, errors):
    if raw in (None, {}, False):
        return None
    if not isinstance(raw, dict):
        errors['intake'] = ['Send the intake ask as an object.']
        return None
    scope = raw.get('scope') or ('selected' if raw.get('keys') else '')
    keys = _strings(raw.get('keys'), 'intake.keys', errors)
    blocks = _strings(raw.get('blocks'), 'intake.blocks', errors)
    if scope and scope not in INTAKE_SCOPES:
        errors['intake.scope'] = [f'Name the intake scope as one of: {", ".join(INTAKE_SCOPES)}.']
    if bad := _unknown(keys, intake_form.KEYS):
        errors['intake.keys'] = [f'Not an intake question: {", ".join(bad)}.']
    if bad := _unknown(blocks, INTAKE_BLOCKS):
        errors['intake.blocks'] = [f'Not a part of the intake: {", ".join(bad)}.']
    if scope == 'selected' and not keys:
        errors['intake.keys'] = ['Pick the intake questions to ask.']
    return {'scope': scope, 'keys': [] if scope == 'all' else keys, 'blocks': blocks}


def _cell(cell):
    """[member id, column] from one sent cell, or None."""
    if not (isinstance(cell, list | tuple) and len(cell) == 2 and isinstance(cell[1], str)):
        return None
    try:
        return [int(cell[0]), cell[1]]
    except (TypeError, ValueError):
        return None


def _cells(raw, errors):
    if raw is None:
        return []
    cells = [_cell(cell) for cell in raw] if isinstance(raw, list) else [None]
    if None in cells:
        errors['census.cells'] = ['Send each cell as [person id, column].']
        return []
    out = []
    for cell in cells:
        if cell not in out:
            out.append(cell)
    if bad := _unknown([column for _member, column in out], census_fields.KEYS):
        errors['census.cells'] = [f'Not a census column: {", ".join(bad)}.']
    if len(out) > CELL_LIMIT:
        errors['census.cells'] = [f'Ask for at most {CELL_LIMIT} census values at once, or ask for their census file.']
    return out


def _clean_census(raw, errors):
    if raw in (None, {}, False):
        return no_census()
    if not isinstance(raw, dict):
        errors['census'] = ['Send the census ask as an object.']
        return no_census()
    scope = raw.get('scope') or 'none'
    if scope not in CENSUS_SCOPES:
        errors['census.scope'] = [f'Name the census scope as one of: {", ".join(CENSUS_SCOPES)}.']
    columns = _strings(raw.get('columns'), 'census.columns', errors)
    if bad := _unknown(columns, census_fields.KEYS):
        errors['census.columns'] = [f'Not a census column: {", ".join(bad)}.']
    cells = _cells(raw.get('cells'), errors)
    if scope == 'selected' and not cells:
        errors['census.cells'] = ['Pick the census values to ask.']
    if raw.get('file') not in (None, True, False):
        errors['census.file'] = ['file must be true or false.']
    return {
        'scope': scope,
        'columns': [] if scope == 'none' else columns,
        'cells': [] if scope in ('none', 'all') else cells,
        'file': raw.get('file') is True,
    }


def _clean_forms(raw, errors):
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        errors['questionnaires'] = ['Send the questionnaires as a list.']
        return []
    out, seen = [], set()
    for entry in raw:
        entry = entry if isinstance(entry, dict) else {}
        key, mode = str(entry.get('form') or ''), entry.get('mode') or 'online'
        if not questionnaire_forms.get_form(key):
            errors['questionnaires'] = [f'Not a questionnaire: {key or "(blank)"}.']
            continue
        if mode not in FORM_MODES:
            errors['questionnaires'] = ['Name each form as online or upload.']
            continue
        picks = entry.get('picks') if isinstance(entry.get('picks'), dict) else {}
        fields = _strings(picks.get('fields'), 'questionnaires.picks', errors)
        blocks = _strings(picks.get('blocks'), 'questionnaires.picks', errors)
        if key not in seen:
            seen.add(key)
            out.append({'form': key, 'mode': mode, 'picks': {'fields': fields, 'blocks': blocks}})
    return out


def slot_valid(slot):
    """True for `<kind>` or `<kind>@<line>` naming a file a client may be asked for."""
    kind, _, line = slot.partition('@')
    if kind not in DOCUMENT_KINDS:
        return False
    return not line or (kind in LINE_KINDS and line in lines.LINE_KEYS)


def _clean_documents(raw, errors):
    if raw in (None, {}, False):
        return no_documents()
    if not isinstance(raw, dict):
        errors['documents'] = ['Send the documents ask as an object.']
        return no_documents()
    slots = _strings(raw.get('slots'), 'documents.slots', errors)
    if bad := [slot for slot in slots if not slot_valid(slot)]:
        errors['documents.slots'] = [f'Not a file a client can be asked for: {", ".join(bad)}.']
    if raw.get('missing') not in (None, True, False):
        errors['documents.missing'] = ['missing must be true or false.']
    return {'slots': slots, 'missing': raw.get('missing') is True}


def clean(raw):
    """(asks in the stored shape, {field: [sentence]}). An ask that asks nothing is an error."""
    errors = {}
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return empty(), {'asks': ['Send the asks as an object.']}
    asks = {
        'intake': _clean_intake(raw.get('intake'), errors),
        'census': _clean_census(raw.get('census'), errors),
        'questionnaires': _clean_forms(raw.get('questionnaires'), errors),
        'documents': _clean_documents(raw.get('documents'), errors),
    }
    if not errors and is_empty(asks):
        errors['asks'] = [NOTHING]
    return asks, errors


def is_empty(asks):
    intake = asks.get('intake') or {}
    census = asks.get('census') or {}
    documents = asks.get('documents') or {}
    return not (
        intake.get('scope')
        or intake.get('blocks')
        or census.get('scope', 'none') != 'none'
        or census.get('file')
        or asks.get('questionnaires')
        or documents.get('slots')
        or documents.get('missing')
    )


def sections(asks):
    """The sections a request carries (D-203): a section's board lists the requests that carry it."""
    asks = asks or {}
    found = set()
    census = asks.get('census') or {}
    if census.get('scope', 'none') != 'none' or census.get('file'):
        found.add('census')
    intake = asks.get('intake') or {}
    documents = asks.get('documents') or {}
    if intake.get('scope') or intake.get('blocks') or documents.get('slots') or documents.get('missing'):
        found.add('intake')  # the checklist's files are the Intake's (D-202)
    if asks.get('questionnaires'):
        found.add('questionnaire')
    return sorted(found)
