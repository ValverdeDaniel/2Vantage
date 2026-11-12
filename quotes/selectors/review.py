"""The station's List of plan values (plan.md §10.7; E34, E56, E57, D121, D122): `GET deals/{id}/plans/sources/`.

Every live plan value whose source names one of the files (or any file, when none is named), worst first: the bucket
(`review_rules.review_bucket`, eight of them), values a person dealt with (approved or ignored) last within it, then the
board's order (the deal's lines in order, each line's plans in `order.layout`'s order, each plan's fields in group
order). The server buckets, counts, orders and pages (200 a page, E56 ch. 24), so a big deal never ships every value.
A row names its plan by carrier and plan name, never a person; values are the plan's (no census data reaches here).

The answer also carries what the panel's head shows (E34, E48, E57): each bucket's open and done counts, the strip's
warning counts (`review_rules.warning_counts`) and the quality headline over the plans the files gave (high = clean
values from the files, low = their open warnings, missing = required blanks on those plans). Reads only (Q.3 #2).
"""

from django.contrib.auth import get_user_model

from deals import lines
from documents import review_rules as rules

from .. import facts, fields
from .state import line_data, load

PAGE_SIZE = 200


def _people(entries):
    ids = set()
    for entry in entries:
        for key in rules.MARK_KEYS:
            by = (entry.get(key) or {}).get('by')
            if by:
                ids.add(by)
    # One query whatever the page holds, so the read costs the same at any size (Q.3 #4); 0 is never a user id.
    users = get_user_model().objects.filter(id__in=sorted(ids) or [0])
    return {user.id: user.get_full_name() or user.username for user in users}


def _stamp(stamp, names):
    if not stamp:
        return None
    return {**stamp, 'by_name': names.get(stamp.get('by'), '')}


def _where(entry):
    loc = entry.get('loc') if isinstance(entry.get('loc'), dict) else {}
    if loc.get('cell'):
        return f'{loc["sheet"]} {loc["cell"]}' if loc.get('sheet') else loc['cell']
    if entry.get('cell') and not loc.get('page'):
        return str(entry['cell']).replace('!', ' ')
    page = loc.get('page') or entry.get('page')
    return f'p. {page}' if page else ''


def _ordered_plans(deal):
    """The deal's live plans with their sources, in the board's order."""
    by_line = {}
    for plan in load(deal, sources=True):
        by_line.setdefault(plan.line, []).append(plan)
    ordered = []
    for line in sorted(by_line, key=lambda key: lines.LINE_KEYS.index(key) if key in lines.LINE_KEYS else 999):
        rows = {plan.id: plan for plan in by_line[line]}
        ordered.extend(rows[p.id] for p in line_data(line, list(rows.values())).plans)
    return ordered


def _items(plans, document_ids):
    """[(plan, key, entry)] for the values from these files, and the plans they came from, in board order."""
    items, gave = [], []
    for plan in plans:
        mine = False
        for key in fields.keys_for(plan.line):
            entry = plan.sources.get(key)
            if key not in plan.values or not isinstance(entry, dict) or not entry.get('doc'):
                continue
            if document_ids is not None and entry['doc'] not in document_ids:
                continue
            items.append((plan, key, entry))
            mine = True
        if mine or (document_ids is not None and plan.source_document_id in document_ids):
            gave.append(plan)
    return items, gave


def _quality(items, gave):
    low = sum(1 for _plan, _key, entry in items if rules.open_warning(entry))
    missing = sum(
        1
        for plan in gave
        for state in facts.statuses(plan.line, plan.values, plan.sources).values()
        if state == 'missing'
    )
    counts = {'high': len(items) - low, 'low': low, 'missing': missing}
    return counts, rules.quality_headline(**counts)


def _row(plan, key, entry, bucket, names):
    label = fields.BY_KEY[key]['label']
    hint = ' '.join(part for part in (plan.carrier, plan.name) if part)
    return {
        'ref': f'plan:{plan.id}:{key}',
        'plan_id': plan.id,
        'key': key,
        'label': label,
        'sub': ' · '.join(part for part in (plan.carrier, plan.name) if part),
        'value': plan.values.get(key, ''),
        'bucket': bucket,
        'where': _where(entry),
        'doc': entry.get('doc'),
        'origin': entry.get('origin'),
        'low': entry.get('low') or None,
        'loc': entry.get('loc') or None,
        'mark': _stamp(entry.get('mark'), names),
        'confirmed': _stamp(entry.get('confirmed'), names),
        'open': rules.open_warning(entry),
        'potential': rules.potential_error(entry),
        'dealt': rules.is_dealt(entry),
        'hint': hint,
        'what': f'{label} · {hint}',
    }


def source_rows(deal, document_ids=None, bucket='', page=1):
    """{rows, page, pages, total, page_size, counts: {bucket: {open, done}}, all: {open, done}, warnings: {open, check,
    unflagged}, quality: {high, low, missing}, headline: {label, tone}}; `rows` are the page's, in the bucket asked."""
    documents = set(document_ids) if document_ids is not None else None
    items, gave = _items(_ordered_plans(deal), documents)
    graded = [
        (rules.BUCKET_ORDER[rules.review_bucket(entry)], rules.is_dealt(entry), index, plan, key, entry)
        for index, (plan, key, entry) in enumerate(items)
    ]
    graded.sort(key=lambda row: row[:3])
    counts = {key: {'open': 0, 'done': 0} for key in rules.BUCKET_KEYS}
    for order, dealt, *_rest in graded:
        counts[rules.BUCKET_KEYS[order]]['done' if dealt else 'open'] += 1
    shown = [row for row in graded if not bucket or rules.BUCKET_KEYS[row[0]] == bucket]
    pages = max(1, -(-len(shown) // PAGE_SIZE))
    window = shown[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
    names = _people([row[5] for row in window])
    quality, headline = _quality(items, gave)
    done = sum(1 for row in graded if row[1])
    return {
        'rows': [_row(plan, key, entry, rules.BUCKET_KEYS[order], names) for order, _d, _i, plan, key, entry in window],
        'page': page,
        'pages': pages,
        'total': len(shown),
        'page_size': PAGE_SIZE,
        'counts': {key: value for key, value in counts.items() if value['open'] or value['done']},
        'all': {'open': len(graded) - done, 'done': done},
        'warnings': rules.warning_counts(entry for _plan, _key, entry in items),
        'quality': quality,
        'headline': headline,
    }
