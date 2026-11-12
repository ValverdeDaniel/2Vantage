"""Work with Claude on Intake (plan.md §10.6; B39; slice 51): the intake turn's context and its writing tool.

- `<intake>` (get intake, verify intake): on the Intake tab, the form as it stands — each question answered, with its
  value, the needed ones still blank, the coverage in force and what the form's own checks say (B8) — so Claude can
  read a document (`read_document`), compare and propose. Employer facts only: no census, no contacts' details.
- `propose_intake_changes` (write fields, write coverage lines): answers and coverage lines as items of the turn's
  change set, in the intake reader's shape (`reader.changes`), so they land the same way (`services.read_apply.land`,
  as Claude's own row, and ↶ Undo this run takes them back). A value the producer said (`dictated`) lands as their own
  hand edit; any other lands as Claude's, flagged to check (B39: "read values land as low-confidence reads"). An
  answer a person stands behind is never written over unless the producer said it: it arrives unticked (D61).
Contacts stay with the intake reader (a contact's rows keep keys only, so a chat's Undo could not take one back).
Registered with the intake reader, behind the PHI-gate switch (§10.8). The tool is sent without `strict` (past the
API's grammar limit, slice 37), so `_checked` validates its whole input in code before anything is staged.
"""

from ai import tools
from ai.registry import Tool
from deals import lines as line_vocab

from . import form, values
from .models import CurrentCoverage, Intake
from .reader.changes import answer_items, coverage_items
from .selectors import answers_of, form_state
from .services.coverage import FUNDING as FUNDING_KEYS

MAX_ANSWERS = 60
COVERAGE_KEYS = ('line', 'carrier', 'funding', 'renewal_date')
PARTS = {'answers': ('key', 'value', 'dictated'), 'coverage': COVERAGE_KEYS}
PROPOSED = 'Claude proposed this in a chat: check it.'
LANDS = 'They go on the form when your turn ends; the producer can undo them.'
WAITS = 'They wait for the producer to review and apply them.'


def _shown(value):
    return ', '.join(value) if isinstance(value, list) else ' '.join(str(value).split())


def _line(row):
    said = f'{row.line}: {row.carrier or "carrier not given"}, {row.funding or "funding not given"}'
    return said + (f', renews {row.renewal_date.isoformat()}' if row.renewal_date else '')


def provide(deal, page):
    """<intake>: the form's answers, the needed blanks, the coverage in force and the form's issues ('' off Intake)."""
    if (page or {}).get('tab') != 'intake':
        return ''
    intake = Intake.objects.filter(deal=deal).first()
    answers = answers_of(deal, intake)
    rows = list(CurrentCoverage.objects.filter(deal=deal).order_by('sort_order', 'id'))
    answered = [
        f'- {key} = {form.BY_KEY[key]["label"]}: {_shown(answers[key])}'
        for key in form.KEYS
        if not values.blank(answers.get(key))
    ]
    state = form_state(deal, intake, rows, {})
    needed = [
        f'{key} ({form.BY_KEY[key]["label"]})'
        for key in state.get('needed') or []
        if key in form.BY_KEY and values.blank(answers.get(key))
    ]
    issues = [
        f'- {form.BY_KEY[key]["label"]}: {entry["message"]}'
        for key, found in (state.get('issues') or {}).items()
        if key in form.BY_KEY
        for entry in found
    ]
    lines = ['<intake>', 'Answered (key = label: value):', *(answered or ['(none yet)'])]
    lines.append('Needed and still blank: ' + (', '.join(needed) or 'none'))
    lines.append('Coverage in force: ' + ('; '.join(_line(row) for row in rows) or 'none recorded'))
    lines += ["The form's checks say:", *(issues or ['(nothing)']), '</intake>']
    return '\n'.join(lines)


def _checked(data):
    """{answers, coverage}: the input checked against the tool's schema in code, before anything is staged. The tool
    is sent without `strict` (past the API's grammar limit, slice 37), so Claude may send any shape: an unknown field,
    a part that is not a list of objects, an object with fields of its own, an answer without its key, a line of
    coverage or a funding that does not exist each refuse the whole call with a sentence (D81). A part left out is
    empty, and `dictated` left out is false (a value the producer did not say)."""
    unknown = sorted(set(data) - set(PARTS))
    if unknown:
        raise tools.ToolRefused(f'Unknown input: {", ".join(unknown)}. Send answers and coverage.')
    parts = {}
    for name, fields in PARTS.items():
        rows = tools.objects(data[name], name) if data.get(name) not in (None, '') else []
        for row in rows:
            extra = sorted(set(row) - set(fields))
            if extra:
                raise tools.ToolRefused(f'Each of {name} takes {", ".join(fields)}; not {", ".join(extra)}.')
        parts[name] = rows
    if not parts['answers'] and not parts['coverage']:
        raise tools.ToolRefused('Send the answers or the coverage lines to propose.')
    for row in parts['answers']:
        if not tools.text(row.get('key'), 'An answer’s key', 60):
            raise tools.ToolRefused('Each answer takes the key of its intake question.')
        if 'dictated' in row:
            tools.boolean(row['dictated'], 'dictated')
    for row in parts['coverage']:
        line = tools.text(row.get('line'), 'A coverage line', 40)
        if line not in line_vocab.BY_KEY:
            raise tools.ToolRefused(f'"{line}" is not a line of coverage.')
        funding = tools.text(row.get('funding'), 'Funding', 40)
        if funding and funding not in FUNDING_KEYS:
            raise tools.ToolRefused(f'Funding is one of {", ".join(sorted(FUNDING_KEYS))}, or blank.')
    return parts


def _answers(rows, refused):
    fields = {}
    for raw in rows[:MAX_ANSWERS]:
        key = tools.text(raw.get('key'), 'An answer’s key', 60)
        if key not in form.BY_KEY:
            refused.append(f'"{key}" is not an intake question.')
            continue
        dictated = tools.boolean(raw['dictated'], 'dictated') if 'dictated' in raw else False
        fields[key] = {
            'value': tools.text(raw.get('value'), 'An answer', 500),
            'low': None if dictated else PROPOSED,
            'dictated': dictated,
            'proposed': True,
        }
    return fields


def _coverage(rows):
    return [{key: tools.text(raw.get(key), key.replace('_', ' '), 200) for key in COVERAGE_KEYS} for raw in rows[:12]]


def propose_intake_changes(turn, data):
    parts = _checked(data)
    refused, findings = [], []
    items = answer_items(turn.deal, _answers(parts['answers'], refused), findings)
    items += coverage_items(turn.deal, _coverage(parts['coverage']), findings)
    for item in items:
        verb = 'Set' if item['op'] == 'answer' else 'Coverage:'
        turn.add({**item, 'owner': 'intake', 'label': f'{verb} {item["label"]}'})
    said = [
        f'Proposed {len(items)} change{"s" if len(items) != 1 else ""} to Intake.' if items else 'Nothing to change.'
    ]
    left = sum(1 for item in items if not item['tick'])
    if left:
        said.append(f'{left} arrive unticked: a person stands behind the answer on the deal.')
    said += refused + [finding['text'] for finding in findings]
    if items:
        said.append(LANDS if turn.lands else WAITS)
    return ' '.join(said)


TOOL = Tool(
    name='propose_intake_changes',
    owner='intake',
    order=55,
    description=(
        'Propose intake answers and current coverage lines from what the producer said or a document shows. answers: '
        'key (an intake question key from <intake> or the form), value as the form takes it, dictated true only when '
        'the producer said the value in this chat. coverage: line (medical, dental, vision, life, std, ltd...), '
        "carrier, funding (fully_insured, level_funded, self_funded or ''), renewal_date (MM/DD/YYYY or ''). Never "
        'propose a census person, a medical detail or a contact here.'
    ),
    schema=tools.schema(
        {
            'answers': {
                'type': 'array',
                'items': tools.schema(
                    {'key': {'type': 'string'}, 'value': {'type': 'string'}, 'dictated': {'type': 'boolean'}}
                ),
            },
            'coverage': {
                'type': 'array',
                'items': tools.schema({key: {'type': 'string'} for key in COVERAGE_KEYS}),
            },
        }
    ),
    run=propose_intake_changes,
)
