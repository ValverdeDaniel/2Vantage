"""The board's config: what a saved setup stores and what Claude's `set_board` may set (plan.md §6.7; F14–F28; the old
pipeline/advisor_filters.py). Pure: `clean_config(raw, view)` returns the config every reader can trust, or raises
`ConfigError` naming each refused key. A key the board has no control for is refused, never stored.

The quotes config (one object; the browser keeps it in the URL and applies a saved one whole):
- `find`: the finder's words (F14); `budget_pct`: a rung of `board_presets.BUDGET` (F18) or None;
- `rules`: [{key, op, value, line?}] (F19, F24): `total` or a plan field, an operator of `RULE_OPS` for its kind, a
  number or a phrase; `line` keeps a rule to one line ("Monthly total ≤ $" is the rule {total, <=, value, line});
- `sliders`: {field: number} for the keys of `SLIDERS` (F20); `ee_rate_max`, `copay_max`: numbers or None (F21);
- `hide`: keys of `HIDES`; `starred_only`, `needs_check`, `to_review`: switches (F22); `carriers`: names (F23);
- `preset`, `sort` {key, dir}, `layout` ('rows' or 'cols'): the columns, the order and ⇄ Transpose (F31–F34).
Claude's pick names plans, so it is never part of a config (F25).

The stop-loss board's config (F29; slice 36; the old cleaner's stop-loss branch), the second entry in CLEANERS:
`rank_by` (a key of `stop_loss_board.RANK_KEYS`), `annual_mode`, `show_terms` and `hide_unscored` (switches). The
laser what-if is never part of it (F104).
"""

import copy
import math
import re

from deals import lines

from . import board_presets as presets
from . import fields, stop_loss_board

MAX_FIND = 120
MAX_CARRIERS = 30
MAX_CARRIER = 120
MAX_RULE_TEXT = 60
LAYOUTS = ('rows', 'cols')
SPECIAL_SORTS = tuple(key for key, _ in presets.SORTS if key)
_NUMBER = re.compile(r'^\$?\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*%?$')


class ConfigError(ValueError):
    """{key: sentence} for each refused key, so a form can show each message beside its control."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__('; '.join(f'{key}: {sentence}' for key, sentence in errors.items()))


def _number(value):
    """2000, '2,000' and '$2,000' are numbers; anything else (a bool, a range, a phrase, inf) is None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
    else:
        found = _NUMBER.match(str(value or '').strip())
        if not found:
            return None
        out = float(found.group(1).replace(',', ''))
    if not math.isfinite(out):
        return None
    return int(out) if out == int(out) else out


def _amount(value, label):
    """A cap or slider: None (no limit) or a number at or above 0."""
    if value in (None, ''):
        return None
    number = _number(value)
    if number is None or number < 0:
        raise ValueError(f'{label} takes a dollar amount, not "{value}".')
    return number


def _switch(value, label):
    if not isinstance(value, bool):
        raise ValueError(f'{label} is on or off (true or false).')
    return value


def _text(value, limit, label):
    if not isinstance(value, str):
        raise ValueError(f'{label} takes text.')
    text = value.strip()
    if len(text) > limit:
        raise ValueError(f'{label} takes at most {limit} characters.')
    return text


def _list(value, label):
    if not isinstance(value, (list, tuple)):
        raise ValueError(f'{label} takes a list.')
    return value


def rule_kind(key):
    """'number' or 'text' for a key a rule may name, else None."""
    if key == presets.TOTAL:
        return 'number'
    field = fields.BY_KEY.get(key)
    return presets.RULE_KINDS.get(field['type']) if field else None


_OPS = {op['key']: op['kind'] for op in presets.RULE_OPS}


def _rule(raw):
    if not isinstance(raw, dict) or set(raw) - {'key', 'op', 'value', 'line'}:
        raise ValueError('Each rule is {key, op, value, line?}.')
    key = raw.get('key')
    kind = rule_kind(key) if isinstance(key, str) else None
    if kind is None:
        raise ValueError(f'"{key}" is not a column a rule can name.')
    op = presets.RULE_OP_ALIASES.get(raw.get('op'), raw.get('op'))
    if _OPS.get(op) != kind:
        usable = ', '.join(key for key, of in _OPS.items() if of == kind)
        raise ValueError(f'"{raw.get("op")}" does not apply to {raw.get("key")}: use {usable}.')
    if kind == 'number':
        value = _number(raw.get('value'))
        if value is None:
            raise ValueError(f'A rule on {key} takes one number, not "{raw.get("value")}".')
    else:
        value = _text(raw.get('value'), MAX_RULE_TEXT, f'A rule on {key}') if raw.get('value') is not None else ''
        if not value:
            raise ValueError(f'A rule on {key} takes a phrase.')
    rule = {'key': key, 'op': op, 'value': value}
    line = raw.get('line') or ''
    if line:
        if line not in lines.BY_KEY:
            raise ValueError(f'"{line}" is not a line of coverage.')
        rule['line'] = line
    return rule


def _rules(value):
    out, seen = [], set()
    for raw in _list(value, 'Rules'):
        rule = _rule(raw)
        marker = (rule['key'], rule['op'], str(rule['value']).lower(), rule.get('line', ''))
        if marker not in seen:
            seen.add(marker)
            out.append(rule)
    if len(out) > presets.MAX_RULES:
        raise ValueError(f'The board holds at most {presets.MAX_RULES} rules.')
    return out


_SLIDER_KEYS = {slider['key']: slider['label'] for group in presets.SLIDERS.values() for slider in group}


def _sliders(value):
    if not isinstance(value, dict):
        raise ValueError('Sliders take {field: amount}.')
    out = {}
    for key, raw in value.items():
        if key not in _SLIDER_KEYS:
            raise ValueError(f'"{key}" has no slider.')
        amount = _amount(raw, _SLIDER_KEYS[key])
        if amount is not None:
            out[key] = amount
    return out


def _budget(value):
    if value in (None, ''):
        return None
    rungs = [rung['value'] for rung in presets.BUDGET if rung['value'] is not None]
    number = _number(value)
    if number not in rungs:
        raise ValueError(f'The budget is one of {", ".join(str(rung) for rung in rungs)}, or none.')
    return number


def _hide(value):
    keys = [hide['key'] for hide in presets.HIDES]
    asked = _list(value, 'Hide')
    unknown = [key for key in asked if key not in keys]
    if unknown:
        raise ValueError(f'Nothing called "{unknown[0]}" can be hidden.')
    return [key for key in keys if key in asked]


def _carriers(value):
    out = []
    for name in _list(value, 'Carriers'):
        text = _text(name, MAX_CARRIER, 'A carrier')
        if text and text not in out:
            out.append(text)
    if len(out) > MAX_CARRIERS:
        raise ValueError(f'At most {MAX_CARRIERS} carriers.')
    return out


_SORTABLE = {
    *SPECIAL_SORTS,
    *(column['key'] for column in presets.PINNED if column['sort']),
    *(column['key'] for column in presets.DERIVED if column['sort']),
    *fields.BY_KEY,
}


def _sort(value):
    if not isinstance(value, dict) or set(value) - {'key', 'dir'} or value.get('key') not in _SORTABLE:
        raise ValueError('The sort is {key, dir}: a sort of the board or a column it can sort on.')
    direction = value.get('dir', 1)
    if direction not in (1, -1) or isinstance(direction, bool):
        raise ValueError('The sort direction is 1 (ascending) or -1 (descending).')
    return {'key': value['key'], 'dir': direction}


def _choice(choices, label):
    def clean(value):
        if value not in choices:
            raise ValueError(f'{label} is one of {", ".join(choices)}.')
        return value

    return clean


QUOTES = {
    'find': (lambda value: _text(value, MAX_FIND, 'The finder'), ''),
    'budget_pct': (_budget, None),
    'rules': (_rules, []),
    'sliders': (_sliders, {}),
    'ee_rate_max': (lambda value: _amount(value, 'The EE-only rate cap'), None),
    'copay_max': (lambda value: _amount(value, 'The PCP copay cap'), None),
    'hide': (_hide, []),
    'starred_only': (lambda value: _switch(value, 'Starred only'), False),
    'needs_check': (lambda value: _switch(value, 'Needs checking'), False),
    'to_review': (lambda value: _switch(value, 'To review'), False),
    'carriers': (_carriers, []),
    'preset': (_choice([key for key, _ in presets.PRESETS], 'The columns'), presets.DEFAULT_PRESET),
    'sort': (_sort, {'key': presets.DEFAULT_SORT, 'dir': 1}),
    'layout': (_choice(LAYOUTS, 'The layout'), 'rows'),
}
STOP_LOSS = {
    'rank_by': (_choice(stop_loss_board.RANK_KEY_SET, 'Rank by'), stop_loss_board.SETTINGS['rank_by']),
    'annual_mode': (lambda value: _switch(value, 'Annual only'), stop_loss_board.SETTINGS['annual_mode']),
    'show_terms': (lambda value: _switch(value, 'Contract terms'), stop_loss_board.SETTINGS['show_terms']),
    'hide_unscored': (lambda value: _switch(value, 'Hide unscored'), stop_loss_board.SETTINGS['hide_unscored']),
}
CLEANERS = {'quotes': QUOTES, stop_loss_board.VIEW: STOP_LOSS}


def defaults(view='quotes'):
    """A config with nothing set: every filter off, the default columns, order and layout."""
    return {key: copy.deepcopy(default) for key, (_, default) in CLEANERS[view].items()}


def clean_config(raw, view='quotes', partial=False):
    """The config `raw` means, every key checked; missing keys take their defaults unless `partial` (a patch, which
    cleans only the keys it names). Raises ConfigError for an unknown view, an unknown key or a bad value."""
    if view not in CLEANERS:
        raise ConfigError({'view': f'There are no saved setups for "{view}" yet.'})
    if not isinstance(raw, dict):
        raise ConfigError({'config': 'The setup is {setting: value}.'})
    cleaners = CLEANERS[view]
    errors = {key: f'"{key}" is not a board setting.' for key in raw if key not in cleaners}
    out = {} if partial else defaults(view)
    for key, (clean, _) in cleaners.items():
        if key not in raw:
            continue
        try:
            out[key] = clean(raw[key])
        except ValueError as exc:
            errors[key] = str(exc)
    if errors:
        raise ConfigError(errors)
    return out
