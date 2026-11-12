"""A census import as the mapping dialog reads it (plan.md §5.3.2, §7.7; C14, C15).

`import_row` is the light entry the census page lists. `import_payload` adds what is read from the stored file for
this answer only and never stored (§5.3.2 step 4): up to three sample values per column, the workbook's sheets, and
the reformat's things worth checking, which name people. The file's name is shown to the person mapping it; it never
reaches Activity, a log or an error (§3.8).
"""

from documents.selectors import display_name
from documents.sheets import column_letter

from .. import fields, pivot
from ..importer import read
from ..services import rows


def import_row(imp):
    document = imp.document
    return {
        'id': imp.id,
        'status': imp.status,
        'document_id': imp.document_id,
        'document_name': display_name(document) if document else '',
        'created_at': imp.created_at.isoformat(),
        'applied_at': imp.applied_at.isoformat() if imp.applied_at else None,
        'stats': imp.stats,
        'needs_attention': pivot.needs_attention(imp.pivot),
        'reformatted': bool((imp.pivot or {}).get('applied')),
    }


def import_payload(imp):
    """The import with its samples (read from the file now), sheets and reformat (§7.7 GET / PATCH)."""
    found = rows.opened(imp)
    table = found.table
    mapped = [item['column'] for item in imp.mapping if item['field'] and item['column'] < len(table.headers)]
    mapping = [
        {
            **item,
            'letter': column_letter(item['column']) if not found.recipe.get('applied') else '',
            'label': fields.label(item['field']) if item['field'] else '',
            'samples': read.samples(table, item['column']) if item['column'] < len(table.headers) else [],
        }
        for item in imp.mapping
    ]
    return {
        **import_row(imp),
        'deal_id': imp.deal_id,
        'sheet_name': imp.sheet_name,
        'sheets': found.names,
        'header_row': imp.header_row,
        'first_data_row': imp.first_data_row,
        'headers': imp.headers,
        'rows': sum(1 for row in table.rows if any(row[column] for column in mapped)),
        'mapping': mapping,
        'mapped': sum(1 for item in imp.mapping if item['field']),
        'pivot': {**(imp.pivot or {}), 'conflicts': found.conflicts},
    }
