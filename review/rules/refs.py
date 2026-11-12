"""The refs a decision names (plan.md §5.8, §7.13; L.6; slice 55). Pure. The same refs as `requests.carries` and the
portal: `intake:<question key>`, `intake:block:<contacts|coverage|lines>`, `census:<member id>:<column>`, and
`census:<member id>:*` for a whole person a client added.

`split(refs)` → {'intake': [slot], 'census': [(member id, column)]} in the order given, each once; a ref that is not
one of these raises `Bad` with the refs it refused (the view answers 400 naming them, never echoing more than 20).
"""

from census import fields as census_fields
from census.models import PERSON
from intake import client_view
from intake import form as intake_form

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


def ref_of(surface, slot):
    if surface == 'census':
        member, column = slot
        return f'census:{member}:{column}'
    return f'intake:{slot}'
