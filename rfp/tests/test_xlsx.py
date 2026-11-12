"""The XML patcher against the carriers' own workbooks (plan.md §9.8 "Writing"; K90, K91, K107). Ported from old
Vantage 891f1b3 `XlsxFillTests` and `ExportTypingTests`, on the four census workbooks (the request forms are slice
46's)."""

import io
import re
import zipfile
from datetime import date

import openpyxl
import pytest

from rfp.formats import bundled, translate
from rfp.xlsx import as_csv, package, sheet
from rfp.xlsx.refs import FillError, col_index, col_letters, expand_range


def src(name):
    return bundled.raw(name)


def part(content, name):
    return zipfile.ZipFile(io.BytesIO(content)).read(name).decode()


def sheet_xml(content, sheet_name):
    return part(content, package.sheet_parts(content)[sheet_name])


def test_K90_only_the_patched_sheet_and_nothing_else_changes():
    before = src('uhc_census.xlsx')
    out, warnings = package.fill(before, {'Group Info': {'writes': {'A5': 'Example Co.'}}})
    assert warnings == []
    old, new = zipfile.ZipFile(io.BytesIO(before)), zipfile.ZipFile(io.BytesIO(out))
    assert old.namelist() == new.namelist()
    changed = [n for n in old.namelist() if old.read(n) != new.read(n)]
    assert changed == [package.sheet_parts(before)['Group Info']]


def test_K90_values_keep_their_types():
    out, _ = package.fill(
        src('uhc_census.xlsx'),
        {
            'Employee Info': {
                'writes': {'F4': 'Text & <angle> brackets', 'P4': 61500, 'J4': 41.5, 'I4': date(1985, 3, 14)}
            }
        },
    )
    ws = openpyxl.load_workbook(io.BytesIO(out))['Employee Info']
    assert ws['F4'].value == 'Text & <angle> brackets'
    assert ws['P4'].value == 61500
    assert ws['J4'].value == 41.5
    assert ws['I4'].value.date() == date(1985, 3, 14)


def test_K107_text_that_starts_like_a_formula_lands_as_typed_and_never_runs():
    out, _ = package.fill(src('warner_census.xlsx'), {'Census Template': {'writes': {'C7': '=HYPERLINK("x")'}}})
    ws = openpyxl.load_workbook(io.BytesIO(out))['Census Template']
    assert ws['C7'].value == '=HYPERLINK("x")'
    assert ws['C7'].data_type == 's'
    assert '<f>' not in re.search(r'<c r="C7".*?</c>', sheet_xml(out, 'Census Template')).group(0)


def test_K90_a_new_cell_inherits_the_column_style():
    raw = src('warner_census.xlsx')
    found, _shared = package.read_sheet(raw, 'Census Template')
    column_style = found.col_styles.get(col_index('X'))
    assert column_style is not None
    out, _ = package.fill(raw, {'Census Template': {'writes': {'X600': 'Class A'}}})
    cell = re.search(r'<c r="X600"[^>]*', sheet_xml(out, 'Census Template')).group(0)
    assert f's="{column_style}"' in cell


def test_K90_a_formula_is_never_overwritten():
    out, warnings = package.fill(src('uhc_census.xlsx'), {'Employee Info': {'writes': {'A4': 'Employee', 'Z4': 'x'}}})
    assert any('formula' in text for text in warnings)
    ws = openpyxl.load_workbook(io.BytesIO(out))['Employee Info']
    assert ws['A4'].value == 'Employee'
    assert str(ws['Z4'].value).startswith('=')


def test_K90_merges_row_heights_and_the_recalc_flag():
    out, _ = package.fill(
        src('uhc_census.xlsx'),
        {'Group Info': {'writes': {'A5': 'Example'}, 'merges': ['L9:N9'], 'row_heights': {9: 40}}},
        full_calc_on_load=True,
    )
    book = openpyxl.load_workbook(io.BytesIO(out))
    assert 'L9:N9' in [str(r) for r in book['Group Info'].merged_cells.ranges]
    assert book['Group Info'].row_dimensions[9].height == 40
    assert 'fullCalcOnLoad="1"' in part(out, 'xl/workbook.xml')


def test_K90_range_helpers():
    assert (col_index('A'), col_index('AA'), col_letters(27)) == (1, 27, 'AA')
    assert expand_range('A1:B2') == ['A1', 'B1', 'A2', 'B2']
    with pytest.raises(FillError):
        expand_range('1A:B2')


def test_K90_a_number_in_a_text_cell_is_stored_as_text_and_elsewhere_as_a_number():
    out, _ = package.fill(src('aetna_gateway_census.xlsx'), {'Census Input': {'writes': {'C7': 77801, 'A7': 12345}}})
    xml = sheet_xml(out, 'Census Input')
    assert 't="inlineStr"><is><t xml:space="preserve">77801</t>' in re.search(r'<c r="C7".*?</c>', xml).group(0)
    assert '<v>12345</v>' in re.search(r'<c r="A7".*?</c>', xml).group(0)
    out, _ = package.fill(src('uhc_census.xlsx'), {'Employee Info': {'writes': {'E4': 77801, 'P4': 61500}}})
    xml = sheet_xml(out, 'Employee Info')
    assert 't="inlineStr"' in re.search(r'<c r="E4"[^>]*', xml).group(0)
    assert 'inlineStr' not in re.search(r'<c r="P4"[^>]*', xml).group(0)


def test_K90_a_date_in_a_text_cell_is_the_text_a_person_types():
    out, _ = package.fill(src('uhc_census.xlsx'), {'Group Info': {'writes': {'B5': date(2026, 12, 16)}}})
    assert openpyxl.load_workbook(io.BytesIO(out))['Group Info']['B5'].value == '12/16/2026'


def test_K90_clearing_never_creates_and_drops_an_unstyled_cell():
    out, _ = package.fill(src('aetna_gateway_census.xlsx'), {'Census Input': {'clear': ['L27', 'A4', 'AH900']}})
    xml = sheet_xml(out, 'Census Input')
    assert '<c r="L27"' not in xml
    assert re.search(r'<c r="A4" s="\d+"/>', xml)
    assert '<row r="900"' not in xml


def test_K90_a_template_hole_takes_the_style_of_the_nearest_row_below():
    raw = src('warner_census.xlsx')
    out, _ = package.fill(raw, {'Census Template': {'writes': {'D11': 'y'}, 'style_source_row': 7}})
    assert '<c r="D11" s="10" t="inlineStr">' in sheet_xml(out, 'Census Template')


def test_K90_the_dimension_grows_with_the_roster():
    out, _ = package.fill(src('angle_census.xlsx'), {'Sheet1': {'writes': {'B300': 'Late'}, 'style_source_row': 10}})
    assert '<dimension ref="A1:I300"/>' in sheet_xml(out, 'Sheet1')


def test_K90_entry_headers_mirror_excel():
    before = src('uhc_census.xlsx')
    out, _ = package.fill(before, {'Group Info': {'writes': {'A5': 'Example'}}})
    after = zipfile.ZipFile(io.BytesIO(out))
    for info in zipfile.ZipFile(io.BytesIO(before)).infolist():
        twin = after.getinfo(info.filename)
        assert (twin.compress_type, twin.date_time, twin.create_system, twin.create_version, twin.external_attr) == (
            info.compress_type,
            info.date_time,
            0,
            45,
            0,
        ), info.filename
        assert twin.flag_bits == (6 if info.compress_type else 0), info.filename


def test_K90_core_properties_are_stamped_and_the_thumbnail_dropped():
    out, _ = package.fill(
        src('aetna_gateway_census.xlsx'),
        {'Census Input': {'writes': {'A7': 'Bell'}}},
        modified_by='Dana Example',
        drop_parts=['docProps/thumbnail.emf'],
    )
    archive = zipfile.ZipFile(io.BytesIO(out))
    assert 'docProps/thumbnail.emf' not in archive.namelist()
    assert 'thumbnail' not in archive.read('_rels/.rels').decode()
    assert '<cp:lastModifiedBy>Dana Example</cp:lastModifiedBy>' in archive.read('docProps/core.xml').decode()


def test_K90_auto_recalc_only_when_a_patched_sheet_reads_a_written_column():
    uhc = src('uhc_census.xlsx')
    out, _ = package.fill(uhc, {'Employee Info': {'writes': {'R4': 'Employee Only'}}}, full_calc_on_load='auto')
    assert 'fullCalcOnLoad="1"' in part(out, 'xl/workbook.xml')
    out, _ = package.fill(uhc, {'Group Info': {'writes': {'A5': 'Example'}}}, full_calc_on_load='auto')
    assert 'fullCalcOnLoad' not in part(out, 'xl/workbook.xml')
    out, _ = package.fill(
        src('aetna_gateway_census.xlsx'), {'Census Input': {'writes': {'A7': 'Bell'}}}, full_calc_on_load='auto'
    )
    assert 'fullCalcOnLoad' not in part(out, 'xl/workbook.xml')


def test_K90_a_cloned_style_puts_its_alignment_before_protection():
    styles = '<cellXfs count="1"><xf numFmtId="0" fontId="0"><protection locked="0"/></xf></cellXfs>'
    out, ids = package._clone_styles(styles, {'notes': (0, {'vertical': 'top', 'wrapText': '1'})})
    clone = re.findall(r'<xf\b[^>]*?(?:/>|>.*?</xf>)', out, re.S)[ids['notes']]
    assert clone.index('<alignment') < clone.index('<protection')
    assert 'count="2"' in out and 'applyAlignment="1"' in clone


def test_K91_a_sheet_renders_as_excel_saves_it_as_csv_utf8():
    out, _ = package.fill(
        src('angle_census.xlsx'),
        {'Sheet1': {'writes': {'B10': 'Jane', 'F10': date(1990, 1, 1), 'G10': 33333, 'C11': '=1+1'}}},
    )
    data, fenced = as_csv.sheet_to_csv(out, 'Sheet1')
    assert data.startswith(b'\xef\xbb\xbf')
    lines = data.decode('utf-8-sig').split('\r\n')
    assert lines[8].split(',')[1] == 'First Name*'
    assert lines[9].split(',')[1:3] == ['Jane', 'Doe']
    assert '01/01/1990' in lines[9] and '33333' in lines[9]
    assert lines[10].split(',')[2] == "'=1+1" and fenced == ['C11']


def test_K92_the_type_a_keystroke_leaves():
    assert translate.shaped('77801-1234', 'zip5') == '77801'
    assert translate.shaped('7801', 'zip5') == '07801'
    assert translate.shaped('N/A', 'zip5') == 'N/A'
    assert translate.shaped('quinn', 'initial') == 'Q'
    assert translate.typed({'transform': 'zip5'}, '33101') == 33101
    assert translate.typed({'transform': 'zip5'}, '07030') == '07030'
    assert translate.typed({'transform': 'date'}, '03/14/1985') == date(1985, 3, 14)
    assert translate.typed({'field': 'annual_salary'}, '$61,500') == 61500
    assert translate.typed({'source': 'derive:age'}, '41') == 41
    assert translate.typed({'field': 'first_name'}, '007') == '007'


def test_K90_the_text_style_index_reads_custom_and_builtin_text_formats():
    styles = (
        '<numFmts count="1"><numFmt numFmtId="164" formatCode="@"/></numFmts>'
        '<cellXfs count="3"><xf numFmtId="0"/><xf numFmtId="49"/><xf numFmtId="164"/></cellXfs>'
    )
    assert sheet.text_styles(styles) == frozenset({1, 2})
