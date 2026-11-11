"""The Excel plan template: export and all-or-nothing import (plan.md §9.3)."""

import io
import re

from django.db import transaction
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from deals import lines

from . import fields, selectors, services
from . import values as cleaning
from .models import Plan

HEADER_ROWS = [
    (4, 'Plan ID', 'id'),
    (5, 'Role', 'role'),
    (6, 'Carrier', 'carrier'),
    (7, 'Plan name', 'name'),
    (8, 'Plan number', 'plan_number'),
    (9, 'Renews / replaces plan IDs', 'link'),
]
FIRST_FIELD_ROW = 11
FIRST_PLAN_COLUMN = 3
EMPTY_COLUMNS = 3
GREY = PatternFill('solid', fgColor='E7E9EE')
RISKY = ('=', '+', '-', '@', '\t', '\r')


def sheet_name(line_key):
    return re.sub(r'[\[\]:*?/\\]', '-', lines.label(line_key))[:31]


def put(ws, row, column, value):
    """Write a value; text that a spreadsheet would read as a formula is written as literal text (§3.8)."""
    cell = ws.cell(row=row, column=column)
    if isinstance(value, str) and value.startswith(RISKY):
        cell.value = value
        cell.data_type = 's'
        cell.quotePrefix = True
    else:
        cell.value = value
    return cell


def _link(plan):
    if plan.role == 'renewal':
        return str(plan.renews_id or '')
    return ', '.join(str(p.id) for p in plan.replaces.all())


def export(deal, line=None):
    workbook = Workbook()
    workbook.remove(workbook.active)
    keys = (
        [line]
        if line
        else list(
            dict.fromkeys(
                list(deal.requested_lines) + list(Plan.objects.filter(deal=deal).values_list('line', flat=True))
            )
        )
    )
    keys = [k for k in lines.LINE_KEYS if k in keys]
    for key in keys:
        ws = workbook.create_sheet(sheet_name(key))
        put(ws, 1, 1, f'{deal.client.name} — {lines.label(key)} plans').font = Font(bold=True, size=13)
        put(ws, 2, 1, "Fill one column per plan. Don't change columns A–B.")
        rows = [(row, label, field_key) for row, label, field_key in HEADER_ROWS]
        rows += [(FIRST_FIELD_ROW + i, fields.BY_KEY[k]['label'], k) for i, k in enumerate(fields.keys_for(key))]
        for row, label, field_key in rows:
            put(ws, row, 1, label)
            put(ws, row, 2, field_key).fill = GREY
        plans = selectors.ordered_plans(deal, key)
        for index, plan in enumerate(plans):
            column = FIRST_PLAN_COLUMN + index
            header = {
                'id': plan.id,
                'role': plan.role,
                'carrier': plan.carrier,
                'name': plan.name,
                'plan_number': plan.plan_number,
                'link': _link(plan),
            }
            for row, _, field_key in rows:
                value = header[field_key] if field_key in header else plan.values.get(field_key, '')
                number = cleaning.as_float(value) if field_key not in header and value != '' else None
                put(ws, row, column, number if number is not None and _numeric(field_key) else value)
        ws.column_dimensions['A'].width = 34
        ws.column_dimensions['B'].width = 22
        for index in range(len(plans) + EMPTY_COLUMNS):
            ws.column_dimensions[get_column_letter(FIRST_PLAN_COLUMN + index)].width = 22
        ws.freeze_panes = 'C1'
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _numeric(key):
    return fields.BY_KEY[key]['type'] in ('amount', 'percent', 'rate', 'rate4', 'number')


def _text(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _line_for(sheet):
    for line in lines.LINES:
        if sheet.strip().lower() in (line['key'], line['label'].lower(), sheet_name(line['key']).lower()):
            return line['key']
    return None


def _ids(text):
    return [int(part) for part in re.split(r'[,\s]+', text) if part.isdigit()]


def read(deal, content):
    """Parse and validate a filled template. Returns (operations, errors); writes nothing."""
    try:
        workbook = load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        return [], [{'sheet': '', 'cell': '', 'message': 'That file is not an Excel workbook (.xlsx).'}]
    operations, errors = [], []
    for ws in workbook.worksheets:
        line = _line_for(ws.title)
        if not line:
            errors.append({'sheet': ws.title, 'cell': '', 'message': f'Sheet "{ws.title}" isn\'t a line of coverage'})
            continue
        allowed = {key for _, _, key in HEADER_ROWS} | set(fields.keys_for(line))
        row_keys = {}
        for row in range(4, ws.max_row + 1):
            key = _text(ws.cell(row=row, column=2).value)
            if not key:
                continue
            if key not in allowed:
                errors.append({'sheet': ws.title, 'cell': f'B{row}', 'message': f'unknown field "{key}"'})
            else:
                row_keys[key] = row
        existing = {p.id: p for p in Plan.objects.filter(deal=deal, line=line).prefetch_related('replaces')}
        currents = {pid for pid, p in existing.items() if p.role == 'current'}
        for column in range(FIRST_PLAN_COLUMN, ws.max_column + 1):
            letter = get_column_letter(column)
            head = {
                key: _text(ws.cell(row=row_keys[key], column=column).value) if key in row_keys else ''
                for _, _, key in HEADER_ROWS
            }
            if not (head['id'] or head['carrier'] or head['name']):
                continue

            def where(key, letter=letter, rows=row_keys):
                return f'{letter}{rows[key]}'

            plan = None
            if head['id']:
                plan = existing.get(int(head['id'])) if head['id'].isdigit() else None
                if not plan:
                    errors.append(
                        {
                            'sheet': ws.title,
                            'cell': where('id'),
                            'message': f"{head['id']} isn't a plan on this deal's {lines.label(line)} line",
                        }
                    )
                    continue
            role = head['role'].lower() or (plan.role if plan else '')
            if not plan:
                for key, label in (('role', 'Role'), ('carrier', 'Carrier'), ('name', 'Plan name')):
                    if not head[key]:
                        errors.append(
                            {
                                'sheet': ws.title,
                                'cell': where(key) if key in row_keys else letter,
                                'message': f'{label} is required for a new plan',
                            }
                        )
            if role and role not in services.ROLES:
                errors.append(
                    {
                        'sheet': ws.title,
                        'cell': where('role'),
                        'message': f'Role "{role}" is not one of current, renewal, alternate',
                    }
                )
                continue
            link_ids = _ids(head['link'])
            if head['link'] and (not set(link_ids) <= currents or (role == 'renewal' and len(link_ids) != 1)):
                errors.append(
                    {
                        'sheet': ws.title,
                        'cell': where('link'),
                        'message': 'The link must name current plans on this line (one for a renewal)',
                    }
                )
            values, cells = {}, {}
            for key, row in row_keys.items():
                if key in dict((k, 1) for _, _, k in HEADER_ROWS):
                    continue
                raw = ws.cell(row=row, column=column).value
                if raw in (None, ''):
                    continue  # a blank cell leaves the value unchanged
                value, error = cleaning.clean(key, _text(raw))
                if error:
                    errors.append({'sheet': ws.title, 'cell': f'{letter}{row}', 'message': error})
                else:
                    values[key], cells[key] = value, f'{ws.title}!{letter}{row}'
            operations.append(
                {
                    'line': line,
                    'plan': plan,
                    'role': role,
                    'head': head,
                    'links': link_ids,
                    'values': values,
                    'cells': cells,
                }
            )
    return operations, errors


def _changed_cells(plan, values):
    return sum(1 for key, value in values.items() if plan is None or plan.values.get(key) != value)


def _detail_changes(op):
    """An existing plan's carrier, name, number, role and links that the file changes; what it repeats is left out."""
    plan, head, role, ids = op['plan'], op['head'], op['role'], op['links']
    data = {
        key: head[key] for key in ('carrier', 'name', 'plan_number') if head[key] and head[key] != getattr(plan, key)
    }
    if role == 'renewal':
        links, same = {'renews_id': ids[0] if ids else None}, plan.renews_id == (ids[0] if ids else None)
    else:
        links, same = {'replaces_ids': ids}, sorted(ids) == sorted(p.id for p in plan.replaces.all())
    if role != plan.role or (head['link'] and not same):
        data.update({'role': role, **links})
    return data


@transaction.atomic
def apply(user, deal, operations, document):
    created = updated = cells = 0
    for op in operations:
        head, plan = op['head'], op['plan']
        link = (
            {'renews_id': op['links'][0] if op['links'] else None}
            if op['role'] == 'renewal'
            else {'replaces_ids': op['links']}
        )
        if plan is None:
            services.create_plan(
                user,
                deal,
                line=op['line'],
                role=op['role'],
                carrier=head['carrier'],
                name=head['name'],
                plan_number=head['plan_number'],
                values=op['values'],
                source_origin='import',
                document=document,
                cells=op['cells'],
                **link,
            )
            created += 1
            cells += len(op['values'])
            continue
        data = {'values': op['values'], **_detail_changes(op)}
        _, changed = services.update_plan(user, plan.id, data, 'import', document, op['cells'])
        if changed or len(data) > 1:
            updated += 1
        cells += len(changed)
    return {'create': created, 'update': updated, 'cells_changed': cells}


def dry_run(operations):
    created = sum(1 for op in operations if op['plan'] is None)
    updates = [op for op in operations if op['plan'] is not None]
    cells = [_changed_cells(op['plan'], op['values']) for op in updates]
    return {
        'create': created,
        'update': sum(1 for op, n in zip(updates, cells, strict=True) if n or _detail_changes(op)),
        'cells_changed': sum(cells) + sum(len(op['values']) for op in operations if op['plan'] is None),
    }
