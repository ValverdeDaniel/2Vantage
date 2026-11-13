"""The refs a decision names (plan.md §5.8, §7.13; L.6; slice 55). Pure. The same refs as `requests.carries` and the
portal: `intake:<question key>`, `intake:block:<contacts|coverage|lines>`, `census:<member id>:<column>`, and
`census:<member id>:*` for a whole person a client added.

`split(refs)` → {'intake': [slot], 'census': [(member id, column)]} in the order given, each once; a ref that is not
one of these raises `Bad` with the refs it refused (the view answers 400 naming them, never echoing more than 20).

What a note is about (slice 56: notes, asks in the tray, the client's questions) is one of these refs or a file the
client is asked for: `census:file` (their census file) and `doc:<slot>` (`invoice@medical`, `claims`). A note keeps
it as (surface, key, member): `note_of(ref)` and `ref_of_note(surface, key, member_id)` turn one into the other.
"""

from census import fields as census_fields
from census.models import PERSON
from intake import client_view
from intake import form as intake_form

from .asks import INTAKE_BLOCKS

SURFACES = ('intake', 'census')  # chain order: decisions lock and write them in this order (O.3.7)
LIMIT = 5000  # one decision's refs at most (old GROUP_ID_CAP)


class Bad(ValueError):
    def __init__(self, refs):
        self.refs = list(refs)[:20]
        super().__init__(', '.join(self.refs))


def _intake(rest):
    return rest if rest in intake_form.KEYS or rest in client_view.BLOCK_SLOTS else None


def _census(rest):
    member, _, column = rest.partition(':')
    if not member.isdigit() or len(member) > 18:
        return None
    if column != PERSON and column not in census_fields.BY_KEY:
        return None
    return int(member), column


PARSERS = {'intake': _intake, 'census': _census}


def split(refs):
    if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
        raise Bad(['Send the refs as a list of text.'])
    out = {surface: [] for surface in SURFACES}
    bad = []
    for ref in dict.fromkeys(refs):
        surface, _, rest = ref.partition(':')
        parsed = PARSERS[surface](rest) if surface in PARSERS else None
        if parsed is None:
            bad.append(ref[:80])
        else:
            out[surface].append(parsed)
    if bad:
        raise Bad(bad)
    return out


CENSUS_FILE = 'census_file'  # a note about their census file: the census surface, no person
NOTE_SURFACES = ('intake', 'census', 'documents')  # the questionnaire joins with slice 58


def note_of(ref):
    """(surface, key, member id or None) a note about `ref` keeps, or None for a ref that names nothing a note can be
    about. Says nothing of whether it is on the deal: `selectors.items.resolve` does."""
    if not isinstance(ref, str) or len(ref) > 200:
        return None
    area, _, rest = ref.partition(':')
    if area == 'doc' and rest:
        return 'documents', rest, None
    if ref == 'census:file':
        return 'census', CENSUS_FILE, None
    if area == 'intake' and rest.startswith('block:'):
        return ('intake', rest, None) if rest.removeprefix('block:') in INTAKE_BLOCKS else None
    if area in PARSERS:
        parsed = PARSERS[area](rest)
        if parsed is None or (area == 'census' and parsed[1] == PERSON):
            return None
        return (area, parsed, None) if area == 'intake' else ('census', parsed[1], parsed[0])
    return None


def ref_of_note(surface, key, member_id):
    if surface == 'documents':
        return f'doc:{key}'
    if surface == 'census':
        return 'census:file' if key == CENSUS_FILE else f'census:{member_id}:{key}'
    return f'{surface}:{key}'


def ref_of(surface, slot):
    if surface == 'census':
        member, column = slot
        return f'census:{member}:{column}'
    return f'intake:{slot}'
