"""What Claude answers when it reads a filled carrier form (plan.md §10.4; G99; slice 52). Data.

The old `record_questionnaire` tool at 891f1b3 (one forced tool call per chunk, a property per field), as one
structured output that is the same bytes for every form, deal and file, so it caches and stays small (a grammar of one
property per field of three forms would not):
- `answers`: each question the file answers — its field key, the answer as written, the page it is printed on (the
  file's page number) and whether Claude was unsure of it (the old `unsure` list and `answer_pages`, D-145, D-152);
- `rows`: each filled row of a repeating section in printed order — its block, its page, and its values, each with
  its field key and Claude's doubt.
Keys are the carrier's own field names, so an answer maps onto its slot with no mapping layer; the enums are every
form's keys, and the code keeps only the keys of the form the file fills (merge.py). A structured-output schema
allows no bounds.
"""

from .. import forms
from ..engine.spec import block_fields, block_keys, section_fields

VERSION = 1


def _keys(fields):
    return [field['key'] for field in fields if not field.get('auto')]


def _union(lists):
    return list(dict.fromkeys(key for keys in lists for key in keys))


ANSWER_KEYS = _union(_keys(section_fields(form)) for form in forms.FORMS.values())
BLOCKS = _union(block_keys(form) for form in forms.FORMS.values())
ROW_KEYS = _union(_keys(block_fields(form, block)) for form in forms.FORMS.values() for block in block_keys(form))


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


ANSWER = _object(
    {
        'key': {'type': 'string', 'enum': ANSWER_KEYS},
        'value': {'type': 'string'},
        'page': {'type': 'integer'},
        'unsure': {'type': 'boolean'},
    }
)
ROW_VALUE = _object(
    {
        'key': {'type': 'string', 'enum': ROW_KEYS},
        'value': {'type': 'string'},
        'unsure': {'type': 'boolean'},
    }
)
ROW = _object(
    {
        'block': {'type': 'string', 'enum': BLOCKS},
        'page': {'type': 'integer'},
        'values': {'type': 'array', 'items': ROW_VALUE},
    }
)
SCHEMA = _object({'answers': {'type': 'array', 'items': ANSWER}, 'rows': {'type': 'array', 'items': ROW}})
