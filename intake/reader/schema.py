"""What Claude answers when it reads a client's company document for Intake (plan.md §10.4; B40, D112; slice 51). Data.

The old `record_intake` tool at 891f1b3, as a structured output, in three parts:
- `fields`: each intake answer the document prints (`key`, §4.5), the value as printed, its page (a PDF's page number,
  else 0), its cell in a spreadsheet ('' otherwise) and whether Claude was unsure;
- `coverage`: the coverage the group has today, one entry per line, with carrier, funding, renewal date and page;
- `contacts`: the named benefits, HR or decision-making contacts, with their role when the document says it.
The schema is the same bytes for every deal and file (it caches); a structured-output schema allows no bounds.
"""

from deals import contacts as contact_vocab
from deals import lines as line_vocab

from .. import form

VERSION = 1
KEYS = tuple(form.KEYS)  # never the client guidance: that is the producer's words (D98)
FUNDING = ('', *(key for key, _label in line_vocab.FUNDING))
ROLES = ('', *contact_vocab.LABELS)


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


FIELD = _object(
    {
        'key': {'type': 'string', 'enum': list(KEYS)},
        'value': {'type': 'string'},
        'page': {'type': 'integer'},
        'cell': {'type': 'string'},
        'unsure': {'type': 'boolean'},
    }
)
COVERAGE = _object(
    {
        'line': {'type': 'string', 'enum': list(line_vocab.LINE_KEYS)},
        'carrier': {'type': 'string'},
        'funding': {'type': 'string', 'enum': list(FUNDING)},
        'renewal_date': {'type': 'string'},
        'page': {'type': 'integer'},
    }
)
CONTACT = _object(
    {
        'name': {'type': 'string'},
        'title': {'type': 'string'},
        'email': {'type': 'string'},
        'phone': {'type': 'string'},
        'role': {'type': 'string', 'enum': list(ROLES)},
    }
)
SCHEMA = _object(
    {
        'fields': {'type': 'array', 'items': FIELD},
        'coverage': {'type': 'array', 'items': COVERAGE},
        'contacts': {'type': 'array', 'items': CONTACT},
    }
)
