"""What Claude answers when it reads a census roster (plan.md §10.4; C19, D110; slice 51). Data.

One answer lists every person the pages print, in printed order, each dependent right after the employee it is printed
under (the old `record_census_members` tool at 891f1b3, as a structured output):
- `dependent`: whether the person is an employee's dependent;
- `employee`: for a dependent, the employee it is listed under, first and last name as printed ('' for an employee),
  so a dependent at the top of a page is never filed under the wrong person (the old D-152);
- `values`: the person's values, each with the census column it fills (`key`, §4.4), the value as printed, the page it
  is printed on (the file's page number) and whether Claude was unsure of it.
The schema is the same bytes for every deal and file, so it caches; a structured-output schema allows no bounds.
"""

from .. import fields

VERSION = 1
KEYS = tuple(fields.KEYS)


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


VALUE = _object(
    {
        'key': {'type': 'string', 'enum': list(KEYS)},
        'value': {'type': 'string'},
        'page': {'type': 'integer'},
        'unsure': {'type': 'boolean'},
    }
)
PERSON = _object(
    {
        'dependent': {'type': 'boolean'},
        'employee': {'type': 'string'},
        'values': {'type': 'array', 'items': VALUE},
    }
)
SCHEMA = _object({'people': {'type': 'array', 'items': PERSON}})
