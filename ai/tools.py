"""Claude's chat tools: the list a turn sends, and running one call (plan.md §10.6; D81, O.3.3; slice 24).

Tools are strict (`strict: true`: the API holds Claude to each input schema) and validated again in code, because a
schema cannot say "a plan of this deal" or "a field of that line". Owners register them (`registry.register_tool`);
`specs()` lists them in their fixed order, the same bytes on every deal, so they stay in the cached prefix. A tool's
`run(turn, data)` answers in words for Claude; a refusal (`ToolRefused`) goes back as an error result Claude can act
on. Any other failure is logged by its class only (rule 10) and answers a fixed sentence.

The parsers below take what a tool's schema allows and the forms Claude sometimes writes instead — a number as text
("$40,000", "41"), a list as JSON text ('[41, 42]') or as "41, 42" — so a tool never fails on the wrapping of a value
(the old app's string tool inputs, Q.9).
"""

import json
import logging
import re

from . import registry

logger = logging.getLogger(__name__)

FAILED = 'That did not work, so nothing changed. Say what you need in other words, or tell the producer.'
UNKNOWN = 'There is no tool called that.'
_NUMBER = re.compile(r'^\$?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)$')


class ToolRefused(Exception):  # noqa: N818 - a refusal, said to Claude
    def __init__(self, sentence):
        super().__init__(sentence)
        self.sentence = sentence


def specs():
    """The tools as the API takes them, in their fixed order."""
    ordered = sorted(registry.tools.values(), key=lambda tool: (tool.order, tool.name))
    return [
        {'name': tool.name, 'description': tool.description, 'input_schema': tool.schema, 'strict': True}
        for tool in ordered
    ]


def run(turn, block):
    """(result text, is_error) for one tool_use block."""
    tool = registry.tools.get(block.get('name'))
    if tool is None:
        return UNKNOWN, True
    data = block.get('input')
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            data = None
    if not isinstance(data, dict):
        return 'The input must be an object.', True
    try:
        return str(tool.run(turn, data)), False
    except ToolRefused as exc:
        return exc.sentence, True
    except Exception as exc:  # noqa: BLE001 - the class only, never its text (rule 10)
        logger.warning('The %s tool failed: %s', tool.name, exc.__class__.__name__)
        return FAILED, True


# ---- the parsers ---------------------------------------------------------------------------------------------------
def _loads(value):
    if isinstance(value, str) and value.strip()[:1] in ('[', '{'):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def integer(value, label):
    if isinstance(value, bool):
        raise ToolRefused(f'{label} takes a whole number.')
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    text = str(value or '').strip()
    if re.fullmatch(r'-?\d+', text):
        return int(text)
    raise ToolRefused(f'{label} takes a whole number, not "{str(value)[:40]}".')


def number(value, label):
    """A number from 2000, '2000', '2,000' or '$2,000'."""
    if isinstance(value, bool):
        raise ToolRefused(f'{label} takes a number.')
    if isinstance(value, (int, float)):
        return value
    found = _NUMBER.match(str(value or '').strip())
    if not found:
        raise ToolRefused(f'{label} takes a number, not "{str(value)[:40]}".')
    out = float(found.group(1).replace(',', ''))
    return int(out) if out.is_integer() else out


def listed(value, label):
    """A list from a list, its JSON text, or comma-separated text."""
    value = _loads(value)
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str):
        return [part.strip() for part in value.split(',') if part.strip()]
    raise ToolRefused(f'{label} takes a list.')


def integers(value, label):
    return [integer(item, label) for item in listed(value, label)]


def text(value, label, limit):
    if value is None:
        return ''
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ToolRefused(f'{label} takes text.')
    out = ' '.join(str(value).split()) if limit <= 300 else str(value).strip()
    if len(out) > limit:
        raise ToolRefused(f'{label} takes at most {limit:,} characters.')
    return out


def boolean(value, label):
    if isinstance(value, bool):
        return value
    if str(value).strip().lower() in ('true', 'false'):
        return str(value).strip().lower() == 'true'
    raise ToolRefused(f'{label} is true or false.')


def objects(value, label):
    """A list of objects (a list, or its JSON text)."""
    items = listed(_loads(value), label)
    items = [_loads(item) for item in items]
    if any(not isinstance(item, dict) for item in items):
        raise ToolRefused(f'Each of {label} is an object.')
    return items


def schema(properties, required=None):
    """A closed object schema; every property is required unless `required` names fewer."""
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': list(properties if required is None else required),
        'properties': properties,
    }
