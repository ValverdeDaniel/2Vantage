"""The change set a quote read proposes (plan.md §10.5; D.6's shape; D56, D59–D62, D64, D115, D117, F138, F143).

Nothing is written here: the change set waits in the job for a person (slice 18), and `read_apply` lands the ticked
items through the Advisor's services (slice 19). Items follow the quote's reading order (F138), so plans it adds are
numbered in that order and the board opens as the carrier printed it (D62). One item per plan the read found:
- `create_plan`: no plan on the deal is this one. A current plan is created only on a line with no current plan; on a
  line that has one, the item asks which it is (`pick_current`, unticked) — never a duplicate current plan (D117).
  A renewal renews its current plan (`renews`: an item of this read or a plan on the deal); a renewal whose current
  plan the file does not show becomes an alternate. A quote's `replaces` comes from the file, unticked when unsure.
- `set_values`: it matched a plan (`match.py`); only values that change are listed (D60), each ticked or left alone.
Then `counts.py` adds the printed tier counts (OQ30) and the lines no one asked for (D56); `locating.py` finds every
value in its file (E79). The plans from these files the read did not return are listed as `kept` (D60). Last,
`read_checks` adds its findings (D88; slice 24): a hard one steps the read up to Opus 5.5 where allowed (D76).
The set also carries the printed tables (`layout`, D66: item ids in printed column order, rows in printed order, the
printed cells of rows that fill no field, none for PHI kinds), which `read_apply` keeps as `QuoteLayout` (slice 21),
and each PDF's printed page numbers where they differ from its pages (`page_labels`, E94).
"""

from documents.kinds import PHI_KINDS
from documents.pages import printed_labels

from .. import fields, read_checks, split
from . import counts as count_items
from . import locating, rules
from .match import match, ref_key
from .schema import VERSION

PICK = 'This line already has current plans: pick the one this is, or add it as another current plan.'
NO_CURRENT = 'The file shows no current plan for this renewal, so it is read as an alternate.'
REPLACES_UNSURE = 'Check which plan this quote replaces.'


class Builder:
    def __init__(self, deal, plans, files, sbc_docs=()):
        self.deal, self.plans, self.files = deal, plans, files
        self.sbc_docs = set(sbc_docs)  # the deal's SBC files: their values beat a quote's (D47)
        self.items, self.findings, self.kept = [], [], []
        self.by_key = {}  # merged plan key -> item
        self.matched = set()
        self.dropped = 0

    def next_id(self):
        return f'i{len(self.items) + 1}'

    def current_of(self, found):
        """The renewal's current plan: (item or None, plan or None)."""
        item = self.by_key.get(found.get('renews'))
        if item is None:
            return None, None
        return item, next((plan for plan in self.plans if plan.id == item.get('plan')), None)

    def staged(self, found, plan=None):
        line_keys = rules.keys_of(found['line'])
        staged = []
        for key, entry in found['values'].items():
            if key not in line_keys:
                self.dropped += 1
                continue
            old_value = (plan.values or {}).get(key) if plan else None
            old_source = (plan.sources or {}).get(key) if plan else None
            value, problem = rules.staged_value(
                key,
                entry,
                old_value=old_value,
                old_source=old_source,
                frozen=bool(plan and plan.sold),
                sbc_docs=self.sbc_docs,
            )
            if problem:
                self.findings.append({'text': f'{found["carrier"]} {found["name"]}: {problem}', 'hard': False})
            if value and value['why'] == rules.LEFT_ALONE['sbc']:
                label = fields.BY_KEY.get(key, {}).get('label', key)
                self.findings.append(
                    {
                        'text': f'{found["carrier"]} {found["name"]}: the quote prints {label} as {value["new"]}, '
                        f'its SBC as {value["old"]}; the SBC’s value stays.',
                        'hard': False,
                    }
                )
            if value:
                staged.append(value)
        order = {key: number for number, key in enumerate(fields.keys_for(found['line']))}
        return sorted(staged, key=lambda value: order.get(value['key'], 999))

    def add(self, found, op, role, plan=None, **extra):
        item = {
            'id': self.next_id(),
            'op': op,
            'plan': plan.id if plan else None,
            'line': found['line'],
            'role': role,
            'carrier': found['carrier'],
            'name': found['name'],
            'plan_number': found['plan_number'],
            'codes': found['codes'],
            'read_ref': ref_key(found),
            'docs': found['docs'],
            'renews': None,
            'replaces': None,
            'values': self.staged(found, plan),
            'unmapped': found['unmapped'],
            'tick': True,
            'stale': False,
            'frozen': bool(plan and plan.sold),
            'why': '',
            **extra,
        }
        self.items.append(item)
        self.by_key[found['key']] = item
        return item

    def plan_item(self, found):
        current_item, current_plan = self.current_of(found) if found['side'] == 'renewal' else (None, None)
        plan, how = match(found, self.plans, renews_plan=current_plan)
        if plan is not None:
            self.matched.add(plan.id)
            item = self.add(found, 'set_values', plan.role, plan, matched=how)
            if not item['values'] and not item['frozen']:
                item['tick'] = False
                item['why'] = 'Nothing in this read differs from the plan.'
            return item
        if found['side'] == 'current':
            others = [p for p in self.plans if p.line == found['line'] and p.role == 'current']
            if others:
                options = [{'plan': p.id, 'label': f'{p.carrier} {p.name}'} for p in others]
                return self.add(found, 'pick_current', 'current', options=options, tick=False, why=PICK)
            return self.add(found, 'create_plan', 'current')
        if found['side'] == 'renewal':
            if current_item is None:
                return self.add(found, 'create_plan', 'alternate', why=NO_CURRENT)
            item = self.add(found, 'create_plan', 'renewal')
            label = f'{current_item["carrier"]} {current_item["name"]}'
            target = {'plan': current_item['plan']} if current_item['plan'] else {'item': current_item['id']}
            item['renews'] = {**target, 'label': label}
            return item
        item = self.add(found, 'create_plan', 'alternate')
        item['replaces'] = self.replaces(found)
        return item

    def replaces(self, found):
        """What a quote replaces, from the file's words (D115): ticked only when one current plan is named surely."""
        text = found['replaces']
        if not text:
            return None
        words = text.lower()
        named = [p for p in self.plans if p.line == found['line'] and p.role == 'current' and p.name.lower() in words]
        named_items = [
            i
            for i in self.items
            if i['line'] == found['line']
            and i['role'] == 'current'
            and i['op'] == 'create_plan'
            and i['name'].lower() in words
        ]
        to = [{'plan': p.id, 'label': f'{p.carrier} {p.name}'} for p in named] + [
            {'item': i['id'], 'label': f'{i["carrier"]} {i["name"]}'} for i in named_items
        ]
        sure = len(to) == 1 and not found['unsure']
        return {'to': to, 'text': text[:200], 'tick': sure, 'why': '' if sure else REPLACES_UNSURE}

    def kept_plans(self, documents):
        for plan in self.plans:
            came = plan.source_document_id in documents or (plan.read_ref or {}).get('doc') in documents
            if came and plan.id not in self.matched:
                self.kept.append({'plan': plan.id, 'label': f'{plan.carrier} {plan.name}', 'line': plan.line})


def sbc_documents(deal):
    """The ids of the deal's SBC files, removed ones too (their values still name them)."""
    from documents.models import Document

    return set(Document.all_objects.filter(deal=deal, kind='sbc').values_list('id', flat=True))


def _layouts(merged, builder, files):
    phi = {file.id for file in files if file.kind in PHI_KINDS}
    out = []
    for layout in merged['layouts']:
        columns = [builder.by_key[key]['id'] for key in layout['columns'] if key in builder.by_key]
        rows = [
            {
                'label': row['label'],
                'keys': row['keys'],
                'printed': {}
                if layout['doc'] in phi
                else {builder.by_key[k]['id']: text for k, text in row['printed'].items() if k in builder.by_key},
            }
            for row in layout['rows']
        ]
        out.append({**layout, 'columns': columns, 'rows': rows})
    return out


def _page_labels(files):
    """{document id: {"<pdf page>": "<printed>"}} for the PDFs whose printed page numbers differ from their pages."""
    out = {}
    for file in files:
        if file.extension == '.pdf' and isinstance(file.id, int):
            labels = printed_labels(file.raw, file.texts)
            if labels:
                out[str(file.id)] = labels
    return out


def _summary(items, findings):
    plans = [item for item in items if item['op'] in ('create_plan', 'set_values', 'pick_current')]
    new = [item for item in plans if item['op'] == 'create_plan']
    roles = {}
    for item in new:
        roles[item['role']] = roles.get(item['role'], 0) + 1
    words = {
        'current': ('current plan', 'current plans'),
        'renewal': ('renewal', 'renewals'),
        'alternate': ('quote', 'quotes'),
    }
    parts = [f'{n} {words[role][n != 1]}' for role, n in roles.items()]
    updates = len([item for item in plans if item['op'] == 'set_values' and item['values']])
    if updates:
        parts.append(f'{updates} plan{"s" if updates != 1 else ""} with new values')
    picks = len([item for item in plans if item['op'] == 'pick_current'])
    if picks:
        parts.append(f'{picks} to pick')
    return ' · '.join(parts) or 'Nothing new in this read'


def build_changes(deal, user, merged, files, extra):
    """The change set (D.6): items in reading order, the printed layout, findings, failed parts, left-out pages."""
    from ..models import Plan

    lines = sorted({found['line'] for found in merged['plans']})
    plans = list(Plan.objects.filter(deal=deal).order_by('line', 'sort_order', 'id'))
    builder = Builder(deal, plans, files, sbc_docs=sbc_documents(deal))
    found_plans, aliases, halves = split.prepare(merged['plans'], plans)  # D116: "A / B" plans take both halves
    for found in found_plans:
        builder.plan_item(found)
    builder.by_key.update({alias: builder.by_key[key] for alias, key in aliases.items() if key in builder.by_key})
    builder.findings += halves
    count_items.add(builder, deal, merged, lines)
    builder.kept_plans({file.id for file in files})
    locating.locate_items(builder.items, files)
    for conflict in merged['conflicts']:
        item = builder.by_key.get(conflict['plan'])
        label = fields.BY_KEY.get(conflict['key'], {}).get('label', conflict['key'])
        if item:
            builder.findings.append(
                {
                    'text': f'{item["carrier"]} {item["name"]}: two files print {label} as '
                    f'{conflict["kept"]} and {conflict["other"]}; the newer file is used.',
                    'hard': False,
                }
            )
    builder.findings += read_checks.for_read(builder.items, {plan.id: plan for plan in plans})  # D88 (slice 24)
    if builder.dropped:
        builder.findings.append(
            {
                'text': f'{builder.dropped} value{"s" if builder.dropped != 1 else ""} for '
                'fields their line does not have were left out.',
                'hard': False,
            }
        )
    values = sum(len(item.get('values') or []) for item in builder.items)
    unticked = sum(1 for item in builder.items if not item['tick']) + sum(
        1 for item in builder.items for value in item.get('values') or [] if not value['tick']
    )
    return {
        'v': VERSION,
        'target': 'quotes',
        'documents': [file.id for file in files],
        'summary': _summary(builder.items, builder.findings),
        'counts': {
            'items': len(builder.items),
            'values': values,
            'unticked': unticked,
            'findings': len(builder.findings),
        },
        'items': builder.items,
        'layout': _layouts(merged, builder, files),
        'page_labels': _page_labels(files),
        'kept': builder.kept,
        'findings': builder.findings,
        'landed': {'plan_ids': [], 'areas': []},
        **extra,
    }
