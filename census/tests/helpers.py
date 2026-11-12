"""Synthetic census files for the census tests: small, made by code, never a real file (plan.md §12.1, Q.8)."""

import csv
import io

from django.core.files.uploadedfile import SimpleUploadedFile

from documents import services as documents

HEADERS = ['Emp ID', 'Relationship', 'First Name', 'Last Name', 'DOB', 'Gender', 'Zip', 'Hours', 'Medical Plan', 'Tier']


def xlsx(rows, sheet='Census', more=None):
    """An .xlsx whose first sheet holds `rows` (lists of cells); `more` = {sheet name: rows} adds sheets."""
    import openpyxl

    book = openpyxl.Workbook()
    first = book.active
    first.title = sheet
    for row in rows:
        first.append(row)
    for name, extra in (more or {}).items():
        added = book.create_sheet(name)
        for row in extra:
            added.append(row)
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def csv_bytes(rows, encoding='utf-8-sig'):
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    return out.getvalue().encode(encoding)


def family(ext, last, *, tier='EE', plan='Gold PPO', deps=(), first='Avery', dob='01/15/1980', zip_code='33101'):
    """An employee row and its dependents' rows under HEADERS. deps: [(relationship, first, dob)]."""
    rows = [[ext, 'Employee', first, last, dob, 'F', zip_code, 40, plan, tier]]
    for relationship, name, born in deps:
        rows.append([ext, relationship, name, last, born, 'M', '', '', '', ''])
    return rows


def roster(*families):
    rows = [list(HEADERS)]
    for rows_of_family in families:
        rows += rows_of_family
    return rows


def upload(user, deal, content, name='census (synthetic).xlsx', kind='census'):
    return documents.upload(user, deal, SimpleUploadedFile(name, content), {'kind': kind})


def import_file(user, deal, content, name='census (synthetic).xlsx'):
    """Upload a census file and propose its import (the import door)."""
    from census import services

    document = upload(user, deal, content, name)
    return services.create_import(user, deal.id, document.id)


def imported(user, deal, content, name='census (synthetic).xlsx', changes=None):
    """Upload, propose, optionally change, and apply; returns the applied import."""
    from census import services

    imp = import_file(user, deal, content, name)
    if changes:
        imp, _ = services.update_import(user, imp.id, changes)
    services.apply_import(user, imp.id)
    imp.refresh_from_db()
    return imp
