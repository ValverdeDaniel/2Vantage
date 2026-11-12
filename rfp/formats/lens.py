"""The census format lens (plan.md §8.12; K79–K88; OQ63): each carrier format checked on the Census tab, from the one
row builder the download uses, so the lens shows what the carrier receives. Reads only; writes nothing.

- `formats(deal)`: one list for the Export readiness cards and the lens chips (K79, K80; OQ63 keeps both): each
  format's rows, columns, what we do not store, its cap, whether it is in the packet and who it is for, and how many
  things to fix before it is sent (columns with required blanks, the cap, validation errors). One roster read.
- `detail(deal, key, rows)`: one format: column by column, what fills it, how many of the rows it applies to hold a
  value, the carrier's required blanks, its translation and rules (K87); the gaps and the columns we never write
  (K88); the warnings and translation notes, naming the people on our own screen only (D-143); the first rows with
  their missing cells (K87); the filled share, floored (K83); and the gap queue's items (K84): each required blank's
  own cell, or a derived column's blank inputs, at most 200.
"""

from census import facts as census_facts
from census import fields

from .. import cleaners, services
from ..cards import census as packet
from ..models import RfpRequest
from . import bundled, definitions, describe, fill, rows, scope, translate

MAX_ITEMS = 200
MAX_ROWS = 200
ERRORS = '{n} validation error{s} in the census — fix before sending to the carrier.'


class UnknownFormat(Exception):
    def __init__(self, key):
        super().__init__(key)
        self.valid = [scope.file_key(fmt) for fmt in definitions.DEFINITIONS.values()]


def resolve(key):
    for fmt in definitions.DEFINITIONS.values():
        if scope.file_key(fmt) == key:
            return fmt
    raise UnknownFormat(key)


def _request(deal):
    stored = cleaners.stored(RfpRequest.objects.filter(deal_id=deal.id).first())
    return stored, services.route_now(deal, stored['route'])


def _errors_text(errors):
    return ERRORS.format(n=errors, s='s remain' if errors != 1 else ' remains') if errors else ''


def formats(deal):
    stored, route = _request(deal)
    counts = census_facts.stored(deal.id)
    people = census_facts.people(deal.id)
    members = len(people)
    cards = {card['key']: card for card in packet.rows(stored, route, members)}
    out = []
    for fmt in definitions.DEFINITIONS.values():
        key = scope.file_key(fmt)
        card = cards[key]
        built = rows.build(fmt, people, deal.requested_lines or [], deal.effective_date)
        short = {ci for _ri, ci in built.missing}
        to_fix = len(short) + int(card['capped']) + int(bool(counts['errors']))
        out.append(
            {
                'key': key,
                'kind': 'census',
                'label': fmt['label'],
                'carrier': fmt['carrier'],
                'file_formats': list(fmt['formats']),
                'rows': members,
                'columns': len(fmt['columns']),
                'gaps': len(fmt['gaps']),
                'max_rows': fmt['max_rows'] or None,
                'capped': card['capped'],
                'in_packet': card['include'],
                'required_by': card['required_by'],
                'to_fix': to_fix if members else None,
            }
        )
    return {'formats': out, 'default_key': scope.file_key(definitions.DEFINITIONS[definitions.UNIVERSAL])}


def person_name(person):
    values = person['values']
    name = ' '.join(part for part in (values.get('first_name'), values.get('last_name')) if part)
    return name or 'Someone'


def _column(fmt, ci, column, built, letters, quoted):
    values = [row[ci] for row in built.rows]
    expected = [ri for ri, person in enumerate(built.people) if rows.applies(column, person['kind'], quoted)]
    return {
        'letter': letters[ci],
        'header': column.get('header') or column.get('hint') or '',
        'fills': describe.fills(column),
        'carrier_required': translate.column_required(column),
        'filled': sum(1 for value in values if value),
        'total': len(values),
        'expected': len(expected),
        'blank': sum(1 for ri in expected if not values[ri]),
        'required_blanks': sum(1 for _ri, c in built.missing if c == ci),
        'translation': describe.translation(column),
        'rules': describe.rules_of(column),
    }


def _filled_pct(columns):
    fillable = [column for column in columns if column['fills']['kind'] != 'gap']
    expected = sum(column['expected'] for column in fillable)
    if not expected:
        return 100 if fillable else 0
    return (100 * (expected - sum(column['blank'] for column in fillable))) // expected  # floored: one blank ≠ 100


def _items(fmt, built):
    """The gap queue: a required blank's own cell, or a derived column's blank inputs (never every cell)."""
    out, seen = [], set()
    for ri, ci in built.missing:
        column, person = fmt['columns'][ci], built.people[ri]
        keys = [column['field']] if column.get('field') else [k for k, _how in describe.consumes(column)]
        for key in keys:
            if key not in fields.BY_KEY or str(person['values'].get(key) or '').strip() or (person['id'], key) in seen:
                continue
            seen.add((person['id'], key))
            out.append(
                {
                    'id': f'{person["id"]}:{key}',
                    'member_id': person['id'],
                    'person': person_name(person),
                    'header': column.get('header') or column.get('hint') or '',
                    'field': key,
                    'field_label': fields.label(key),
                    'derived': not column.get('field'),
                }
            )
    return out


def detail(deal, key, limit=50):
    fmt = resolve(key)
    stored, route = _request(deal)
    built = fill.build_rows(deal, fmt)
    quoted = set(deal.requested_lines or ())
    letters = bundled.letters(fmt)
    columns = [_column(fmt, ci, column, built, letters, quoted) for ci, column in enumerate(fmt['columns'])]
    card = next(row for row in packet.rows(stored, route, len(built.rows)) if row['key'] == key)
    named = {person['id']: person_name(person) for person in built.people}
    needs = sorted({k for column, c in zip(fmt['columns'], columns, strict=True) if c['carrier_required'] and c['blank']
                    for k, _how in describe.consumes(column) if k in fields.BY_KEY})  # fmt: skip
    errors = census_facts.stored(deal.id)['errors']
    limit = max(1, min(int(limit), MAX_ROWS))
    items = _items(fmt, built)
    return {
        'key': key,
        'kind': 'census',
        'label': fmt['label'],
        'carrier': fmt['carrier'],
        'version': fmt['version'],
        'file_formats': list(fmt['formats']),
        'sheet': fmt['sheet'],
        'geometry': describe.geometry(fmt),
        'columns': columns,
        'gaps': fmt['gaps'],
        'gap_notes': describe.gap_notes(fmt),
        'not_sent': fmt['not_sent'],
        'warnings': [text for text in [_errors_text(errors), *built.warnings] if text],
        'max_rows': fmt['max_rows'] or None,
        'capped': card['capped'],
        'in_packet': card['include'],
        'required_by': card['required_by'],
        'preview': {
            'headers': [column['header'] for column in columns],
            'letters': letters,
            'rows': built.rows[:limit],
            'total_rows': len(built.rows),
            'missing_cells': [[r, c] for r, c in built.missing if r < limit],
        },
        'filled_pct': _filled_pct(columns),
        'needs': [{'key': k, 'label': fields.label(k)} for k in needs],
        'gap_items': items[:MAX_ITEMS],
        'gap_total': len(items),
        'notes': [
            {
                **{k: note[k] for k in ('code', 'text', 'count', 'header', 'token')},
                'people': [named.get(pk, 'Someone') for pk in note['row_ids'][:20]],
            }
            for note in built.notes
        ],  # fmt: skip
    }
