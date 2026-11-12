"""Joining a read's answers (plan.md §10.4; D57, D62, D66, D116, F138, F143; the old claude_readers._merge_plans). Pure.

Each range of each file answers on its own; `merge` joins them into one list of plans in reading order (files in
upload order, then pages, then the printed columns), so a plan printed on two pages (its design, then its rates) or in
two files is one plan. Two columns are one plan when they sit on the same line and side and share a strong code, a
plan-number half, or the same carrier and name. A value printed twice keeps the first, except that a later file wins
over an earlier one (newer file wins); where they differ, a finding says so.

Also kept: every printed row in order with the fields it fills (the printed layout, need 3), rows that match no field
with their printed cells, and tier counts printed per plan or for the whole line (D67).
"""

import re

from ai import codes

from .schema import NO_RENEWAL, TIERS, WHOLE_LINE

PLACEHOLDER_CARRIER = 'Unknown carrier'
PLACEHOLDER_PLAN = 'Quoted plan'
MAX_LABEL = 120
MAX_PRINTED = 200


def norm(text):
    return re.sub(r'[^a-z0-9]+', ' ', str(text or '').lower()).strip()


def _where(part, block):
    """Where the table is printed: its sheet, or the first page its cells name (else the range's first page)."""
    if part.kind == 'sheet':
        return {'sheet': part.sheet}
    pages = [
        cell['page']
        for row in block.get('rows') or []
        for cell in row.get('cells') or []
        if isinstance(cell.get('page'), int) and cell['page'] > 0
    ]
    if pages:
        return {'page': min(pages)}
    return {'page': part.pages[0]} if part.pages else {}


class Plan:
    def __init__(self, key, line, file, column, order):
        self.key, self.line = key, line
        self.side = column.get('side') or 'quote'
        self.carrier = str(column.get('carrier') or '').strip() or file.carrier or PLACEHOLDER_CARRIER
        self.name = str(column.get('plan_name') or '').strip() or PLACEHOLDER_PLAN
        self.plan_number = str(column.get('plan_number') or '').strip()
        self.codes = codes.as_list([*(column.get('codes') or []), self.plan_number])
        self.replaces = str(column.get('replaces') or '').strip()
        self.unsure = bool(column.get('unsure'))
        self.order, self.docs, self.renews = order, [file.id], None
        self.values, self.unmapped, self.counts = {}, [], {}

    def same(self, line, side, carrier, name, plan_number, column_codes):
        if line != self.line or side != self.side:
            return False
        if codes.overlap(self.codes, column_codes):
            return True
        if codes.number_parts(plan_number) & codes.number_parts(self.plan_number):
            return True
        return norm(name) == norm(self.name) and norm(carrier) in (norm(self.carrier), '')

    def put(self, key, value, file, cell, label, conflicts):
        entry = {
            'value': value,
            'doc': file.id,
            'page': cell.get('page') or None,
            'cell': cell.get('cell') or '',
            'unsure': bool(cell.get('unsure')),
            'label': str(label or '')[:MAX_LABEL],
            'file_order': file.order,
        }
        held = self.values.get(key)
        if held is None:
            self.values[key] = entry
        elif held['value'] != value:
            newer = file.order > held['file_order']
            conflicts.append(
                {
                    'plan': self.key,
                    'key': key,
                    'kept': value if newer else held['value'],
                    'other': held['value'] if newer else value,
                }
            )
            if newer:
                self.values[key] = entry

    def as_dict(self):
        return {
            'key': self.key,
            'line': self.line,
            'side': self.side,
            'carrier': self.carrier,
            'name': self.name,
            'plan_number': self.plan_number,
            'codes': self.codes,
            'replaces': self.replaces,
            'unsure': self.unsure,
            'order': list(self.order),
            'docs': self.docs,
            'renews': self.renews,
            'values': self.values,
            'unmapped': self.unmapped,
            'counts': self.counts,
        }


class Merge:
    def __init__(self):
        self.plans, self.line_counts, self.layouts, self.conflicts = [], {}, {}, []

    def plan_for(self, file, line, column, order):
        side = column.get('side') or 'quote'
        carrier = str(column.get('carrier') or '').strip() or file.carrier
        name = str(column.get('plan_name') or '').strip()
        number = str(column.get('plan_number') or '').strip()
        found = codes.as_list([*(column.get('codes') or []), number])
        for plan in self.plans:
            if plan.same(line, side, carrier, name or PLACEHOLDER_PLAN, number, found):
                if file.id not in plan.docs:
                    plan.docs.append(file.id)
                plan.codes = sorted(set(plan.codes) | set(found))
                return plan
        plan = Plan(f'm{len(self.plans) + 1}', line, file, column, order)
        self.plans.append(plan)
        return plan

    def block(self, file, part, block):
        line = block.get('line')
        local = {}
        first = part.pages[0] if part.pages else part.rows[0] if part.rows else 0
        for column in sorted(block.get('columns') or [], key=lambda c: c.get('col', 0)):
            local[column.get('col')] = self.plan_for(file, line, column, (file.order, first, column.get('col', 0)))
        for column in block.get('columns') or []:
            renews = column.get('renews_col', NO_RENEWAL)
            if renews not in (None, NO_RENEWAL) and renews in local and local[column.get('col')].side == 'renewal':
                local[column.get('col')].renews = local[renews].key
        layout = self.layouts.setdefault(
            (file.id, line), {'doc': file.id, 'line': line, 'where': _where(part, block), 'columns': [], 'rows': []}
        )
        for plan in local.values():
            if plan.key not in layout['columns']:
                layout['columns'].append(plan.key)
        for row in block.get('rows') or []:
            self.row(file, local, layout, row)
        for count in block.get('counts') or []:
            tier, number = count.get('tier'), count.get('count')
            if tier not in TIERS or not isinstance(number, int) or number < 0:
                continue
            if count.get('col') == WHOLE_LINE:
                held = self.line_counts.setdefault(line, {'counts': {}, 'doc': file.id, 'page': count.get('page')})
                held['counts'][tier] = number
            elif count.get('col') in local:
                plan = local[count.get('col')]
                plan.counts[tier] = number
                plan.counts.setdefault('_page', count.get('page'))
                plan.counts.setdefault('_doc', file.id)

    def row(self, file, local, layout, row):
        key, label = row.get('key') or '', str(row.get('label') or '').strip()[:MAX_LABEL]
        printed = {}
        for cell in row.get('cells') or []:
            plan = local.get(cell.get('col'))
            value = str(cell.get('value') or '').strip()
            if plan is None or not value:
                continue
            if key:
                plan.put(key, value, file, cell, label, self.conflicts)
            else:
                text = value[:MAX_PRINTED]
                plan.unmapped.append(
                    {'label': label, 'printed': text, 'page': cell.get('page') or None, 'doc': file.id}
                )
                printed[plan.key] = text
        if label and not any(r['label'] == label and r['keys'] == ([key] if key else []) for r in layout['rows']):
            layout['rows'].append({'label': label, 'keys': [key] if key else [], 'printed': printed})


def merge(parts, files):
    """{'plans': [plan dicts in reading order], 'line_counts': {line: {counts, doc, page}}, 'layouts': [...],
    'conflicts': [...]} from parts [(file, range, data)]."""
    joined = Merge()
    ordered = sorted(parts, key=lambda p: (p[0].order, p[1].pages[0] if p[1].pages else 0, p[1].sheet, p[1].rows))
    for file, part, data in ordered:
        for block in (data or {}).get('lines') or []:
            if block.get('line'):
                joined.block(file, part, block)
    return {
        'plans': [plan.as_dict() for plan in joined.plans],
        'line_counts': joined.line_counts,
        'layouts': list(joined.layouts.values()),
        'conflicts': joined.conflicts,
    }
