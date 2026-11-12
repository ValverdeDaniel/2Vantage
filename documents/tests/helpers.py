"""Small synthetic files and an upload helper for the documents tests (synthetic data only, plan.md §12.1)."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile

import synthetic_files

RATES_PDF = synthetic_files.text_pdf(
    ['Example Health 2027 renewal', 'Prepared for Example Co.'],
    ['Plan Gold PPO 1500', 'Employee only $512.34', 'Family $1,580.47'],
)
ROSTER_PDF = synthetic_files.text_pdf(
    ['Example Health renewal packet', 'Rates and plan summaries follow.'],
    [
        'Employee Name DOB Sex Age Zip',
        'TESTER ALPHA 01/02/1970 M 55 30301',
        'TESTER BRAVO 03/04/1980 F 45 30302',
        'TESTER CHARLIE 05/06/1975 M 50 30303',
    ],
)


def xlsx(rows, title='Rates', hidden_rows=(), hidden_cols=(), extra_sheets=()):
    """An .xlsx (XlsxWriter) with one sheet of `rows`, a bold first row, and any hidden rows (0-based) or columns."""
    from documents import xlsx_safe

    out = io.BytesIO()
    book = xlsx_safe.workbook(out)
    bold = book.add_format({'bold': True, 'bg_color': '#DDEBF7', 'border': 1})
    sheet = book.add_worksheet(title)
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            xlsx_safe.write(sheet, r, c, value, bold if r == 0 else None)
    for r in hidden_rows:
        sheet.set_row(r, None, None, {'hidden': True})
    for c in hidden_cols:
        sheet.set_column(c, c, None, None, {'hidden': True})
    for name, hidden in extra_sheets:
        extra = book.add_worksheet(name)
        extra.write_string(0, 0, 'Extra')
        if hidden:
            extra.hide()
    book.close()
    return out.getvalue()


RATES_XLSX_ROWS = [
    ['Plan', 'Gold PPO 1500', 'Silver HMO 3000'],
    ['Deductible', 1500, 3000],
    ['Employee only', 512.34, 410.5],
    ['Family', 1580.47, 1290],
]


def upload(api, deal, name='quote.pdf', content=RATES_PDF, **meta):
    meta.setdefault('kind', 'quote')
    return api.post(
        f'/api/deals/{deal.id}/documents/', {'file': SimpleUploadedFile(name, content), **meta}, format='multipart'
    )


def stored(user, deal, name='quote.pdf', content=RATES_PDF, kind='quote', **meta):
    from documents import services

    return services.upload(user, deal, SimpleUploadedFile(name, content), {'kind': kind, **meta})
