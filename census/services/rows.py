"""Locks, the stored file and the roster the census services share (plan.md §3.7, O.3.7).

Lock order: the Deal, then the import, then the deal's people by id, then `CensusFacts` (facts.refresh). A census
write's Activity is key-only (§3.7, rule 4): `member:<id>` with the keys that changed, never a value, so Revert
refuses it with a sentence and the grid's own undo (slice 41) is the way back.
"""

from rest_framework.exceptions import APIException

from deals.activity import Refused
from deals.models import Deal
from deals.values import locked
from documents.models import Document

from ..importer import CensusFileError, open_table
from ..models import CensusImport, Member

AREA = 'census'
FILE_GONE = 'The census file is no longer on this deal. Upload it again to import it.'
NOT_PROPOSED = {
    CensusImport.APPLIED: 'This census file was already applied. Import the file again to apply it again.',
    CensusImport.DISCARDED: 'This census import was discarded. Import the file again.',
}


class BadFile(APIException):
    """A census file that cannot be read: 400 with the sentence."""

    status_code = 400
    default_code = 'invalid'


def target(member_id):
    return f'member:{member_id}'


def lock_deal(deal_id):
    return locked(Deal, deal_id)


def lock_import(import_id):
    return locked(CensusImport, import_id)


def lock_members(deal_id):
    """Every person of the deal, removed ones too, locked by id."""
    return list(Member.all_objects.select_for_update().filter(deal_id=deal_id).order_by('id'))


def proposed(imp):
    """Refuse a change to an import that is no longer waiting (409)."""
    if imp.status != CensusImport.PROPOSED:
        raise Refused(NOT_PROPOSED[imp.status])


def file_bytes(imp):
    """(filename, bytes) of the import's file; a removed file still opens, a purged one is gone (409)."""
    document = Document.all_objects.filter(pk=imp.document_id).first() if imp.document_id else None
    if document is None:
        raise Refused(FILE_GONE)
    try:
        with document.file.open('rb') as handle:
            return document.original_name, handle.read()
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise Refused(FILE_GONE) from exc


def opened(imp, **choices):
    """The import's table as stored (or with `choices` over it): sheet, header row, first data row, reformat."""
    name, raw = file_bytes(imp)
    settings = {
        'sheet': imp.sheet_name or None,
        'header_row': imp.header_row,
        'first_data_row': imp.first_data_row,
        'reformat': not (imp.pivot or {}).get('declined'),
    }
    settings.update(choices)
    try:
        return open_table(name, raw, **settings)
    except CensusFileError as exc:
        raise BadFile(str(exc)) from exc


def roster_entries(members):
    """Roster entries as matching reads them (census.matching)."""
    return [
        {
            'id': member.id,
            'kind': member.kind,
            'employee_id': member.employee_id,
            'position': member.position,
            'values': member.values,
            'sources': member.sources,
            'client': member.client,
            'added_by_link': member.added_by_link,
            'removed': member.removed_at is not None,
        }
        for member in members
    ]
