"""Mapping a census file: propose, change, discard (plan.md §5.3.2 steps 1–5, §7.7; C12–C15).

`create_import` reads a census file already on the deal (the import door uploads it first, through documents' one
door) and proposes a mapping — or, for a file applied before, starts from the member's last choices for it (the old
"⟲ Re-map source file" reopened them); an earlier proposal still waiting on the deal is discarded, so the tab has one
mapping to review. `update_import` takes the member's sheet, header row, first data row, "use the original file
instead" and column choices; a new sheet or header row proposes the mapping again. Nothing here stores a sample value.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from deals import activity
from documents.models import Document

from ..importer import mapping as mapper
from ..models import CensusImport
from . import rows

NOT_CENSUS = 'Choose a census file on this deal.'
CHOICES = ('sheet_name', 'header_row', 'first_data_row', 'reformat', 'mapping')


def _row_number(data, key, errors):
    if key not in data:
        return None
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 20000:
        errors[key] = ['Send a row number.']
        return None
    return value


def _changes(data, columns):
    """The member's column choices [{column, field}], checked."""
    raw = data.get('mapping')
    if not isinstance(raw, list):
        raise ValidationError({'mapping': ['Send the columns as a list.']})
    out = []
    for item in raw:
        column = item.get('column') if isinstance(item, dict) else None
        field = item.get('field') if isinstance(item, dict) else None
        if isinstance(column, bool) or not isinstance(column, int) or not 0 <= column < columns:
            raise ValidationError({'mapping': ['Each column must be one of the file’s columns.']})
        if field is not None and not isinstance(field, str):
            raise ValidationError({'mapping': ['Each field must be a census column or blank.']})
        out.append({'column': column, 'field': field or ''})
    return out


def _record(deal, user, imp, action, summary, coalesce=False):
    return activity.record(
        deal,
        user,
        rows.AREA,
        action,
        summary,
        document_id=imp.document_id,
        coalesce_key=f'census:import:{imp.id}' if coalesce else '',
        noun='census mapping choice' if coalesce else '',
    )


def _as_before(imp, document):
    """⟲ Re-map source file, or the same file again: start from the member's last applied choices for this file (its
    sheet, rows, reformat and columns) when the file still reads the same way. True when they were taken."""
    # The last applied is the last made (one proposal at a time on a deal), by id, never by `applied_at`: the clock
    # can step back.
    earlier = CensusImport.objects.filter(document=document, status=CensusImport.APPLIED).order_by('-id').first()
    if earlier is None:
        return False
    reformat = not (earlier.pivot or {}).get('declined')
    found = rows.opened(
        imp,
        sheet=earlier.sheet_name,
        header_row=earlier.header_row,
        first_data_row=earlier.first_data_row,
        reformat=reformat,
    )
    if found.table.headers != earlier.headers:
        return False
    imp.sheet_name, imp.header_row, imp.first_data_row = earlier.sheet_name, earlier.header_row, earlier.first_data_row
    imp.headers, imp.pivot, imp.mapping = earlier.headers, found.recipe, earlier.mapping
    return True


@transaction.atomic
def create_import(user, deal_id, document_id):
    """A proposed import of `document_id` (a census file on the deal). 400 when it is not one or cannot be read."""
    deal = rows.lock_deal(deal_id)
    document = Document.all_objects.filter(pk=document_id, deal_id=deal_id, kind='census').first()
    if document is None:
        raise ValidationError({'document_id': [NOT_CENSUS]})
    imp = CensusImport(
        deal=deal, document=document, created_by=user if getattr(user, 'is_authenticated', False) else None
    )
    if not _as_before(imp, document):
        found = rows.opened(imp, sheet=None, header_row=None, first_data_row=None, reformat=True)
        imp.sheet_name = found.sheet[:100]
        imp.header_row, imp.first_data_row = found.header_row, found.first_data_row
        imp.headers, imp.pivot = found.table.headers, found.recipe
        imp.mapping = mapper.propose(found.table.headers)
    for waiting in CensusImport.objects.select_for_update().filter(deal_id=deal_id, status=CensusImport.PROPOSED):
        waiting.status = CensusImport.DISCARDED
        waiting.save(update_fields=['status'])
    imp.save()
    mapped = sum(1 for item in imp.mapping if item['field'])
    _record(deal, user, imp, 'proposed', f'Mapped a census file: {mapped} of {len(imp.mapping)} columns')
    return imp


def _reshaped(imp, data, errors):
    """Apply the sheet, rows and reformat choices; True when the columns changed (the mapping is proposed again)."""
    sheet = data.get('sheet_name', imp.sheet_name)
    if not isinstance(sheet, str):
        errors['sheet_name'] = ['Send a sheet name.']
        return False
    header = _row_number(data, 'header_row', errors)
    first = _row_number(data, 'first_data_row', errors)
    reformat = data.get('reformat', not (imp.pivot or {}).get('declined'))
    if not isinstance(reformat, bool):
        errors['reformat'] = ['Send true or false.']
    if errors:
        return False
    moved = sheet != imp.sheet_name or (header is not None and header != imp.header_row)
    header = header or (None if sheet != imp.sheet_name else imp.header_row)
    first = first or (None if moved else imp.first_data_row)
    if header and first and first <= header:
        errors['first_data_row'] = ['The first person’s row comes after the header row.']
        return False
    found = rows.opened(imp, sheet=sheet or None, header_row=header, first_data_row=first, reformat=reformat)
    if found.sheet != (sheet or found.sheet):
        errors['sheet_name'] = ['This file has no sheet by that name.']
        return False
    columns_changed = found.table.headers != imp.headers
    imp.sheet_name, imp.header_row, imp.first_data_row = found.sheet[:100], found.header_row, found.first_data_row
    imp.headers, imp.pivot = found.table.headers, found.recipe
    if columns_changed:
        imp.mapping = mapper.propose(found.table.headers)
    return columns_changed


@transaction.atomic
def update_import(user, import_id, data):
    """The member's choices on a proposed import (§7.7 PATCH). Returns (import, changed keys)."""
    imp = CensusImport.objects.get(pk=import_id)
    deal = rows.lock_deal(imp.deal_id)
    imp = rows.lock_import(import_id)
    rows.proposed(imp)
    before = {key: getattr(imp, key) for key in ('sheet_name', 'header_row', 'first_data_row', 'pivot', 'mapping')}
    errors = {}
    if any(key in data for key in CHOICES[:4]):
        _reshaped(imp, data, errors)
    if errors:
        raise ValidationError(errors)
    if 'mapping' in data:
        imp.mapping, problems = mapper.confirm(imp.mapping, _changes(data, len(imp.headers)))
        if problems:
            raise ValidationError({'mapping': problems})
    changed = [key for key, was in before.items() if getattr(imp, key) != was]
    if not changed:
        return imp, []
    imp.save(update_fields=[*changed, 'headers'])
    _record(deal, user, imp, 'mapped', 'Changed', coalesce=True)
    return imp, changed


@transaction.atomic
def discard_import(user, import_id):
    """Set a proposed import aside; the roster is untouched."""
    imp = CensusImport.objects.get(pk=import_id)
    deal = rows.lock_deal(imp.deal_id)
    imp = rows.lock_import(import_id)
    rows.proposed(imp)
    imp.status = CensusImport.DISCARDED
    imp.save(update_fields=['status'])
    _record(deal, user, imp, 'discarded', 'Discarded a census file before applying it')
    return imp
