"""The format definitions against the carriers' own workbooks (plan.md §9.8, Appendix A; K93, K96, K105, K124;
OQ109)."""

import pytest

from census import fields
from deals import carriers as identities
from deals import lines
from rfp import carriers
from rfp.formats import bundled, definitions, describe, translate
from rfp.xlsx.package import read_sheet
from rfp.xlsx.refs import FillError

TOKENS = {
    'tier': {'EE', 'ES', 'EC', 'FAM', 'WAIVE'},
    'gender': {'M', 'F'},
    'status': {'ACTIVE', 'COBRA', 'STCON', 'RETIREE'},
}
RELATIONSHIPS = {'employee', 'spouse', 'child', 'domestic_partner'}


@pytest.mark.parametrize('key', definitions.ORDER)
def test_K93_each_bundled_workbook_is_the_carriers_file_byte_for_byte(key):
    fmt = definitions.DEFINITIONS[key]
    assert bundled.digest(fmt['file']) == bundled.SHA256[fmt['file']]


@pytest.mark.parametrize('key', definitions.ORDER)
def test_K96_every_format_matches_its_bundled_file(key):
    assert bundled.verify(definitions.DEFINITIONS[key])


def test_K96_a_moved_column_fails_the_build_by_name():
    fmt = definitions.DEFINITIONS['aetna_gateway']
    moved = {**fmt, 'columns': [fmt['columns'][1], fmt['columns'][0], *fmt['columns'][2:]]}
    with pytest.raises(FillError, match='A6'):
        bundled.verify(moved)
    relabelled = {**fmt, 'group_info': [{'sheet': 'Census Input', 'cell': 'J1', 'label_cell': 'A1', 'label': 'Nope'}]}
    with pytest.raises(FillError, match='A1'):
        bundled.verify(relabelled)


def test_K93_every_field_is_a_census_key_and_every_line_a_line():
    for fmt in definitions.DEFINITIONS.values():
        for column in fmt['columns']:
            if column.get('field'):
                assert column['field'] in fields.BY_KEY, column
            if column.get('line'):
                assert column['line'] in lines.LINE_KEYS, column
            for key, _how in describe.consumes(column):
                assert key in fields.BY_KEY, column


def test_K93_every_source_and_transform_is_one_the_builder_knows():
    sources = {'row:member_type', 'derive:age', 'derive:county', 'derive:out_of_area'}
    for fmt in definitions.DEFINITIONS.values():
        for column in fmt['columns']:
            source = column.get('source') or ''
            assert not source or source in sources or source.startswith('row:enroll:'), column
            if source.startswith('derive:'):
                assert source.removeprefix('derive:') in describe.DERIVE_INPUTS
            assert (column.get('transform') or '') in ('', 'tier', 'gender', 'status', 'date', 'zip5', 'initial')


def test_K92_every_value_map_spells_tokens_the_builder_makes():
    for fmt in definitions.DEFINITIONS.values():
        for column in fmt['columns']:
            words = set(column.get('value_map') or {})
            if not words:
                continue
            if column.get('transform') in TOKENS:
                assert words <= TOKENS[column['transform']], column
            elif column.get('source') == 'row:member_type':
                assert words == RELATIONSHIPS, column
            elif (column.get('source') or '').startswith('row:enroll:'):
                assert words == {'ENROLL'}, column


def test_K105_every_carriers_census_format_exists_and_rfp_carriers_are_deals_carriers():
    assert set(carriers.ATTRIBUTES) == set(identities.KEYS)
    for key, found in carriers.ATTRIBUTES.items():
        if found['census_format']:
            fmt = definitions.DEFINITIONS[found['census_format']]
            assert fmt['carrier_key'] == key


def test_K88_the_columns_we_never_write_are_still_where_the_carrier_prints_them():
    fmt = definitions.DEFINITIONS['uhc']
    found, shared = read_sheet(bundled.raw(fmt['file']), fmt['sheet'])
    columns = fmt['not_sent']['columns']
    assert columns[0]['letter'] == 'Y'
    for column in columns:
        assert bundled.normalize(found.text_at(f'{column["letter"]}{fmt["header_row"]}', shared)) == column['header']
        assert found.holds_formula(f'{column["letter"]}{fmt["data_row"]}') == column['formula']
    assert all(column.get('home') for column in columns)


def test_OQ109_emp_class_fills_both_warner_class_columns_s_and_x():
    fmt = definitions.DEFINITIONS['warner_census']
    letters = bundled.letters(fmt)
    found, shared = read_sheet(bundled.raw(fmt['file']), fmt['sheet'])
    classes = [
        letter for letter, column in zip(letters, fmt['columns'], strict=True) if column.get('field') == 'emp_class'
    ]
    assert classes == ['S', 'X']
    assert [bundled.normalize(found.text_at(f'{letter}3', shared)) for letter in classes] == ['CLASSES', 'CLASSES']


def test_K124_the_carriers_asterisk_makes_a_column_required():
    assert translate.column_required({'header': '*Gender'})
    assert translate.column_required({'header': 'Zip*'})
    assert translate.column_required({'header': 'Last Name', 'required': True})
    assert not translate.column_required({'header': 'Email'})
