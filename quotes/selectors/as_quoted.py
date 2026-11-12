"""The printed tables of a deal's scanned quotes, as the Advisor's "As quoted" (F42) and Documents' "As in the file"
(E42) draw them (plan.md §7.8, O.3.5; D66; slice 21). Read only.

- `files(deal)`: one entry per table on a file not removed, files in upload order and a file's tables in line order:
  `{document, line, line_label, label, where, page_label, plans, rows, written_at}`.
- `table(deal, document_id, line)`: one table. `columns` are its plans still on the deal, in printed order (`col` the
  printed column, `head` the name as printed, `plan` the id; a plan removed since is left out and counted in
  `left_out`); `rows` come in printed order: a row that fills fields names them in `keys` (their live values are the
  Advisor's, so an edit shows at once), and a row that fills none keeps what the file printed, one cell per column in
  `printed`. A file of a PHI kind shows no printed text. `page_label` is the number printed on the table's page when
  the carrier numbered it differently (E94).
"""

from deals import lines as line_vocab
from documents.kinds import PHI_KINDS
from documents.selectors import display_name

from ..models import Plan, QuoteLayout


def _page_label(document, where):
    page = (where or {}).get('page')
    return str((document.page_labels or {}).get(str(page)) or '') if page else ''


def _order(line):
    return line_vocab.LINE_KEYS.index(line) if line in line_vocab.LINE_KEYS else len(line_vocab.LINE_KEYS)


def files(deal):
    layouts = QuoteLayout.objects.filter(deal=deal, document__archived_at__isnull=True).select_related('document__deal')
    ordered = sorted(layouts, key=lambda layout: (layout.document.uploaded_at, layout.document_id, _order(layout.line)))
    return [
        {
            'document': layout.document_id,
            'line': layout.line,
            'line_label': line_vocab.label(layout.line),
            'label': display_name(layout.document),
            'where': layout.where,
            'page_label': _page_label(layout.document, layout.where),
            'plans': len(layout.columns),
            'rows': len(layout.rows),
            'written_at': layout.written_at,
        }
        for layout in ordered
    ]


def table(deal, document_id, line=''):
    """One table's payload, or None when the deal has no table for that file (and line)."""
    found = QuoteLayout.objects.filter(deal=deal, document_id=document_id).select_related('document__deal')
    layout = (found.filter(line=line) if line else found.order_by('id')).first()
    if layout is None:
        return None
    document = layout.document
    ids = [column['plan'] for column in layout.columns]
    live = set(Plan.objects.filter(deal=deal, id__in=ids).values_list('id', flat=True))
    kept = [at for at, column in enumerate(layout.columns) if column['plan'] in live]
    printed = document.kind not in PHI_KINDS
    rows = []
    for row in layout.rows:
        entry = {'label': row['label'], 'keys': list(row['keys'])}
        if not row['keys']:
            cells = row.get('printed') or []
            entry['printed'] = [cells[at] if printed and at < len(cells) else '' for at in kept]
        rows.append(entry)
    return {
        'document': document.id,
        'line': layout.line,
        'line_label': line_vocab.label(layout.line),
        'label': display_name(document),
        'kind': document.kind,
        'where': layout.where,
        'page_label': _page_label(document, layout.where),
        'written_at': layout.written_at,
        'job': layout.job_id,
        'columns': [layout.columns[at] for at in kept],
        'left_out': len(layout.columns) - len(kept),
        'rows': rows,
    }
