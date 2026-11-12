"""What Claude answers when it reads a quote (plan.md §10.4; D.6's row-major schema, D54, D66, D67, F138, F143). Data.

One answer holds each line of coverage the pages quote, as the carrier printed it:
- `columns`, left to right in reading order (F138): who the plan is (carrier, name, number, codes) and which side of a
  renewal packet it sits on (D117) — `current` (in force today), `renewal` (the carrier's offer for the next year,
  with `renews_col` naming its current column) or `quote` (a new plan, with `replaces` as printed when the file says
  which plan it takes the place of, D115);
- `rows`, top to bottom (need 3): the printed label, the field it fills (`key`, '' when no field matches) and one cell
  per column, each with its page (or sheet cell) and whether Claude was unsure;
- `counts`: tier counts printed for a plan (`col`) or the whole line (`col` -1), never a plan's own enrollment (D67).
The schema is identical for every deal and file (it is cached); a structured-output schema allows no numeric bounds.
"""

from deals import lines as line_vocab

from .. import fields

VERSION = 1
SIDES = ('current', 'renewal', 'quote')
TIERS = ('EE', 'ES', 'EC', 'FAM')
WHOLE_LINE = -1
NO_RENEWAL = -1
# Never read: lasers are typed by a person (D118); plan_number is a column of its own.
NOT_READ = {'sl_lasers', 'plan_number'}
FIELD_KEYS = tuple(field['key'] for field in fields.FIELDS if field['key'] not in NOT_READ)
LINE_KEYS = tuple(line_vocab.LINE_KEYS)


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


CELL = _object(
    {
        'col': {'type': 'integer'},
        'value': {'type': 'string'},
        'page': {'type': 'integer'},
        'cell': {'type': 'string'},
        'unsure': {'type': 'boolean'},
    }
)
ROW = _object(
    {
        'label': {'type': 'string'},
        'key': {'type': 'string', 'enum': [*FIELD_KEYS, '']},
        'cells': {'type': 'array', 'items': CELL},
    }
)
COLUMN = _object(
    {
        'col': {'type': 'integer'},
        'carrier': {'type': 'string'},
        'plan_name': {'type': 'string'},
        'plan_number': {'type': 'string'},
        'codes': {'type': 'array', 'items': {'type': 'string'}},
        'side': {'type': 'string', 'enum': list(SIDES)},
        'renews_col': {'type': 'integer'},
        'replaces': {'type': 'string'},
        'unsure': {'type': 'boolean'},
    }
)
COUNT = _object(
    {
        'col': {'type': 'integer'},
        'tier': {'type': 'string', 'enum': list(TIERS)},
        'count': {'type': 'integer'},
        'page': {'type': 'integer'},
    }
)
LINE = _object(
    {
        'line': {'type': 'string', 'enum': list(LINE_KEYS)},
        'columns': {'type': 'array', 'items': COLUMN},
        'rows': {'type': 'array', 'items': ROW},
        'counts': {'type': 'array', 'items': COUNT},
    }
)
SCHEMA = _object({'lines': {'type': 'array', 'items': LINE}})
