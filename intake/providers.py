"""Provider slots: facts intake needs from apps to its right (plan.md §3.3, O.1, O.6 #2).

intake never imports a right app. Each slot is one function with a default answer, so intake runs and passes its tests
before the right app exists; the right app fills it in its AppConfig.ready() with `fill(name, fn)`. Only intake's
services and payloads call a provider; its pure rules (`coverage`, later `checklist`) take the fact as an argument.

- `headcount(deal_id) -> {count, source, estimate}`, filled by quotes (`facts.enrolled_headcount`, slice 13): the
  checklist tier and the census address rule (B25). The default reads intake's own answers, the tail of O.6 #24's
  order: the enrolled count, else the eligible or the total count as an estimate.
- `census_state(deal_id) -> {has_roster, employees, errors, ok}`, filled by census (slice 12): "Census OK" (B33).
- `questionnaire_items(deal_id) -> {item: {form, source, armed, started, progress, signed, done}}`, filled by
  questionnaire (slice 42): the checklist's form rows (B22, B26).
- `quote_lines(deal_id) -> {line: {presented, sold, current}}`, filled by quotes (slice 11): for every line holding
  plans, how many plans it presents, whether one is sold, and `current` — the carrier and funding of its current
  plans ({carrier, funding}, or None with none), so a coverage row shows them read-only (§6.5). Used by
  `line_states`, `lines_off` and the coverage payload (B24).
"""

ANSWER_ORDER = (('enrolled_count', False), ('employee_count', True), ('total_employees', True))


def _headcount_from_answers(deal_id):
    from .selectors import intake_row

    intake = intake_row(deal_id)
    answers = (intake.answers if intake else None) or {}
    for key, estimate in ANSWER_ORDER:
        raw = str(answers.get(key) or '').strip()
        if raw:
            try:
                count = int(float(raw))
            except ValueError:
                continue
            return {'count': count, 'source': f'intake.{key}', 'estimate': estimate}
    return {'count': None, 'source': '', 'estimate': False}


def _no_census(deal_id):
    return {'has_roster': False, 'employees': 0, 'errors': 0, 'ok': False}


def _no_forms(deal_id):
    return {}


def _no_plans(deal_id):
    return {}


_slots = {
    'headcount': _headcount_from_answers,
    'census_state': _no_census,
    'questionnaire_items': _no_forms,
    'quote_lines': _no_plans,
}
DEFAULTS = dict(_slots)


def fill(name, fn):
    """Called by the right app in AppConfig.ready()."""
    if name not in _slots:
        raise KeyError(f'intake has no provider slot named {name}')
    _slots[name] = fn


def headcount(deal_id):
    return _slots['headcount'](deal_id)


def census_state(deal_id):
    return _slots['census_state'](deal_id)


def questionnaire_items(deal_id):
    return _slots['questionnaire_items'](deal_id)


def quote_lines(deal_id):
    return _slots['quote_lines'](deal_id)
