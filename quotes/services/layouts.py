"""The printed table of a scanned quote, written while a read lands (plan.md §6.7, O.3.5; D66, E42, F42; slice 21).

- `write(deal, job, change_set, landed)` turns the change set's `layout` (one table per file and line: the read's item
  ids in printed column order, the rows in printed order, and the printed cells of rows that fill no field) into
  `QuoteLayout` rows, inside `read_apply`'s transaction. Each column becomes the plan its item landed on (`landed`:
  item id → plan id), else the plan the read matched, when that plan is still on the deal (a re-read whose plan did not
  change); a column whose plan is not on the deal (a quote left unticked) is left out. Two printed rows in a row under
  one label (a deductible's single and family halves) are one row with both keys. A file of a PHI kind keeps no
  printed text. A table equal to the stored one writes nothing; otherwise it replaces it and returns one Activity
  entry for the landing's row, `layout.job` before and after (the read whose table the file shows), and the table it
  replaced (none for a first read), which the job keeps for Undo (its `landed.layouts`).
- `replaced_since(entries)` names the tables a later read replaced since a landing; Undo refuses on them (409), and
  "Undo anyway" leaves them as they are.
- `put_back(entries, before)` is Undo's: each table still as the landing left it goes back to the one it
  replaced, or away when there was none. A table whose file was purged since has nothing to put back.
"""

from datetime import datetime

from deals import clock
from deals.activity import change
from documents.kinds import PHI_KINDS
from documents.models import Document
from documents.selectors import display_name

from ..models import Plan, QuoteLayout

KEY = 'layout.job'  # the read whose printed table the file and line show


def target(document_id, line):
    return f'layout:{document_id}:{line}'


def is_layout(target_text):
    return str(target_text).startswith('layout:')


def _parse(target_text):
    _kind, document_id, line = str(target_text).split(':', 2)
    return int(document_id), line


def snapshot(layout):
    if layout is None:
        return None
    return {
        'where': layout.where,
        'columns': layout.columns,
        'rows': layout.rows,
        'job': layout.job_id,
        'written_at': layout.written_at.isoformat(),
    }


def _columns(table, items, plan_of):
    """[(column, item id)] for the columns whose plan is on the deal, in printed order; one column per plan."""
    out, used = [], set()
    for col, item_id in enumerate(table.get('columns') or []):
        item = items.get(item_id)
        plan_id = plan_of(item) if item else None
        if plan_id is None or plan_id in used:
            continue
        used.add(plan_id)
        out.append(({'col': col, 'plan': plan_id, 'head': str(item.get('name') or '')[:200]}, item_id))
    return out


def _rows(table, item_ids, phi):
    out = []
    for row in table.get('rows') or []:
        label, keys = str(row.get('label') or ''), [key for key in row.get('keys') or [] if key]
        last = out[-1] if out else None
        if keys and last and last['keys'] and last['label'] == label and not set(keys) & set(last['keys']):
            last['keys'] += keys
            continue
        entry = {'label': label, 'keys': keys}
        if not keys and not phi:
            printed = row.get('printed') or {}
            entry['printed'] = [str(printed.get(item_id) or '') for item_id in item_ids]
        out.append(entry)
    return out


def write(deal, job, change_set, landed):
    """([Activity entries], {target: the table each replaced, or None}) for the change set's printed tables."""
    tables = [table for table in change_set.get('layout') or [] if table.get('doc') and table.get('line')]
    if not tables:
        return [], {}
    items = {item['id']: item for item in change_set.get('items') or []}
    matched = {item['plan'] for item in items.values() if item.get('plan')} - set(landed.values())
    live = set(Plan.objects.filter(deal=deal, id__in=matched).values_list('id', flat=True))

    def plan_of(item):
        if item['id'] in landed:
            return landed[item['id']]
        return item['plan'] if item.get('plan') in live else None

    kinds = dict(Document.all_objects.filter(deal=deal, id__in={t['doc'] for t in tables}).values_list('id', 'kind'))
    held = {
        (layout.document_id, layout.line): layout
        for layout in QuoteLayout.objects.select_for_update()
        .filter(deal=deal, document_id__in=list(kinds))
        .order_by('id')
    }
    entries, replaced, now = [], {}, clock.now()
    for table in tables:
        if table['doc'] not in kinds:
            continue
        columns = _columns(table, items, plan_of)
        if not columns:
            continue
        state = {
            'where': dict(table.get('where') or {}),
            'columns': [column for column, _item in columns],
            'rows': _rows(table, [item_id for _column, item_id in columns], kinds[table['doc']] in PHI_KINDS),
        }
        layout = held.get((table['doc'], table['line']))
        if layout is not None and {'where': layout.where, 'columns': layout.columns, 'rows': layout.rows} == state:
            continue
        before = snapshot(layout)
        if layout is None:
            layout = QuoteLayout(deal=deal, document_id=table['doc'], line=table['line'])
        layout.where, layout.columns, layout.rows = state['where'], state['columns'], state['rows']
        layout.job, layout.written_at = job, now
        layout.save()
        key = target(table['doc'], table['line'])
        entries.append(change(key, {KEY: [before['job'] if before else None, job.id]}))
        replaced[key] = before
    return entries, replaced


def _held(entries):
    wanted = [_parse(entry['t']) for entry in entries]
    if not wanted:
        return {}
    rows = QuoteLayout.objects.select_for_update().filter(document_id__in=[doc for doc, _line in wanted]).order_by('id')
    return {(layout.document_id, layout.line): layout for layout in rows}


def _label(document_id):
    document = Document.all_objects.select_related('deal').filter(pk=document_id).first()
    return f'The printed table of “{display_name(document)}”' if document else 'A printed table'


def replaced_since(entries):
    """Labels of the tables these entries wrote that a later read has replaced since."""
    held = _held(entries)
    out = []
    for entry in entries:
        layout = held.get(_parse(entry['t']))
        if layout is not None and layout.job_id != entry['k'][KEY][1]:
            out.append(_label(_parse(entry['t'])[0]))
    return out


def put_back(entries, before):
    """Put each table back as it was before the landing; returns the Activity entries written."""
    held, written = _held(entries), []
    for entry in entries:
        layout = held.get(_parse(entry['t']))
        was, wrote = entry['k'][KEY]
        if layout is None or layout.job_id != wrote:  # purged since, or a later read replaced it ("Undo anyway")
            continue
        earlier = before.get(entry['t'])
        if earlier is None:
            layout.delete()
        else:
            layout.where, layout.columns, layout.rows = earlier['where'], earlier['columns'], earlier['rows']
            layout.job_id = earlier['job']
            layout.written_at = datetime.fromisoformat(earlier['written_at'])
            layout.save()
        written.append(change(entry['t'], {KEY: [wrote, was]}))
    return written
