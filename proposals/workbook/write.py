"""The sheet model written as an .xlsx with XlsxWriter, through `documents.xlsx_safe` (plan.md §9.4; J152, J153).

Text goes through `xlsx_safe.write_text` (string-to-formula, URL and number conversion are off in the workbook), so a
carrier-typed `=…` or a web address stays text; links are formulas of ours (HYPERLINK over cells). Every formula is
written with its stored result (`write_formula(…, value)`), so a viewer that does not calculate (a phone's mail
preview, Outlook's preview pane, Excel's Protected View) shows the app's figures. File settings (J152): the agency as
author, recalculation when the file opens (XlsxWriter's fullCalcOnLoad), the zoom each tab asks for, and the file
opens on the tab the model names, the only one selected.

A model width is the width the file stores, as the old writer (openpyxl) stored it and as `print_plan` measures it
(Excel draws a stored 46 at 322 pixels). XlsxWriter's `set_column` would add Excel's 5-pixel padding on top (46 → 46.71
stored, 327 pixels), so every column would draw and print wider than the print plan reckons; the width is written in
pixels instead (`_pixels`), which stores the model's number.
"""

import io

from documents import xlsx_safe

from .model import BLANK, FORMULA, NUMBER, TEXT

ERROR_TITLE = 'Pick from the list'
ERROR_MESSAGE = 'Pick a plan from the drop-down list.'
PROMPT_TITLE = 'Pick a plan'


class _Formats:
    def __init__(self, workbook):
        self.workbook = workbook
        self.cache = {}

    def __call__(self, style):
        if not style:
            return None
        key = tuple(sorted(style.items()))
        if key not in self.cache:
            self.cache[key] = self.workbook.add_format(dict(style))
        return self.cache[key]


def _pixels(width):
    """The pixels Excel draws a column of this stored width at (print_plan's measure)."""
    return int(float(width) * 7 + 0.5)


def _cell(ws, row, col, cell, look):
    r, c = row - 1, col - 1
    if cell.kind == TEXT:
        xlsx_safe.write_text(ws, r, c, cell.value, look)
    elif cell.kind == NUMBER:
        ws.write_number(r, c, cell.value, look)
    elif cell.kind == FORMULA:
        ws.write_formula(r, c, cell.value, look, cell.result)
    elif cell.kind == BLANK and look is not None:
        ws.write_blank(r, c, None, look)


def _print(ws, setup):
    if not setup:
        return
    if setup['landscape']:
        ws.set_landscape()
    ws.set_paper(setup['paper'])
    ws.set_margins(*setup['margins'])
    if setup['center_h']:
        ws.center_horizontally()
    if setup['header']:
        ws.set_header(setup['header'])
    ws.set_footer(setup['footer'])
    r1, c1, r2, c2 = setup['area']
    ws.print_area(r1 - 1, c1 - 1, r2 - 1, c2 - 1)
    ws.hide_gridlines(2)
    if setup['fit']:
        ws.fit_to_pages(*setup['fit'])
    if setup['scale']:
        ws.set_print_scale(setup['scale'])
    if setup['repeat_rows']:
        ws.repeat_rows(setup['repeat_rows'][0] - 1, setup['repeat_rows'][1] - 1)
    if setup['repeat_cols']:
        ws.repeat_columns(setup['repeat_cols'][0] - 1, setup['repeat_cols'][1] - 1)
    if setup['col_breaks']:
        ws.set_v_pagebreaks(list(setup['col_breaks']))
    if setup['row_breaks']:
        ws.set_h_pagebreaks(list(setup['row_breaks']))


def _sheet(ws, sheet, formats):
    for col, width in sorted(sheet.widths.items()):
        ws.set_column_pixels(col - 1, col - 1, _pixels(width))
    for row, height in sorted(sheet.heights.items()):
        ws.set_row(row - 1, height)
    for r1, c1, r2, c2 in sheet.merges:
        anchor = sheet.get(r1, c1)
        ws.merge_range(r1 - 1, c1 - 1, r2 - 1, c2 - 1, '', formats(anchor.style if anchor else None))
    for (row, col), cell in sorted(sheet.cells.items()):
        _cell(ws, row, col, cell, formats(cell.style))
    for rule in sheet.validations:
        r1, c1, r2, c2 = rule['cells']
        options = {
            'validate': 'list',
            'source': '=' + rule['source'],
            'ignore_blank': True,
            'error_type': 'stop',
            'error_title': ERROR_TITLE,
            'error_message': ERROR_MESSAGE,
        }
        if rule['prompt']:
            options.update({'input_title': PROMPT_TITLE, 'input_message': rule['prompt']})
        ws.data_validation(r1 - 1, c1 - 1, r2 - 1, c2 - 1, options)
    for rule in sheet.highlights:
        r1, c1, r2, c2 = rule['cells']
        ws.conditional_format(
            r1 - 1,
            c1 - 1,
            r2 - 1,
            c2 - 1,
            {
                'type': 'formula',
                'criteria': '=' + rule['condition'],
                'format': formats(rule['style']),
                'stop_if_true': True,
            },
        )
    for image in sheet.images:
        ws.insert_image(
            image['row'] - 1,
            image['col'] - 1,
            image.get('name', 'image.png'),
            {'image_data': io.BytesIO(image['data']), 'x_scale': image['x_scale'], 'y_scale': image['y_scale']},
        )
    if sheet.freeze:
        ws.freeze_panes(sheet.freeze[0] - 1, sheet.freeze[1] - 1)
    if sheet.autofilter:
        r1, c1, r2, c2 = sheet.autofilter
        ws.autofilter(r1 - 1, c1 - 1, r2 - 1, c2 - 1)
    ws.set_zoom(sheet.zoom)
    _print(ws, sheet.print)


def to_bytes(book):
    """The book as .xlsx bytes."""
    buffer = io.BytesIO()
    workbook = xlsx_safe.workbook(buffer, {'in_memory': True})
    workbook.set_properties({'author': book.author, 'title': '', 'company': book.author})
    formats = _Formats(workbook)
    for index, sheet in enumerate(book.sheets):
        ws = workbook.add_worksheet(sheet.title)
        _sheet(ws, sheet, formats)
        if index == book.opens_on:
            ws.activate()
    workbook.close()
    return buffer.getvalue()
