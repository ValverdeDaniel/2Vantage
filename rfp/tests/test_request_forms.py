"""Warner's quote request forms and our cover page, downloaded and read back (plan.md §9.9; K42, K46, K47, K99–K102;
OQ65)."""

import io
from datetime import date

import pytest
from pypdf import PdfReader

from deals.models import AgencySettings
from rfp.forms import fill, maps
from rfp.xlsx import package
from rfp.xlsx.refs import FillError

from .request import ask, body, cell, ctx, get
from .roster import crowd, family

pytestmark = pytest.mark.django_db


@pytest.fixture
def dated(deal):
    deal.effective_date = date(2027, 1, 1)
    deal.save(update_fields=['effective_date'])
    return deal


def test_K99_K100_K101_the_simplified_form_carries_the_header_and_the_bands_count(api, user, dated):
    family(user, dated)
    ask(user, dated, due_date='2026-12-15')
    response = get(api, dated, 'form')
    assert response.status_code == 200
    assert 'Example Co. - Quote request form.xlsx' in response['Content-Disposition']
    content = body(response)
    request = ctx(dated)
    assert cell(content, 'Sheet1', 'D9') == 'Example Co.'
    assert cell(content, 'Sheet1', 'D15') == ('' if request.count is None else str(request.count))
    assert float(cell(content, 'Sheet1', 'H6')) == (date(2027, 1, 1) - date(1899, 12, 30)).days  # a real date
    assert float(cell(content, 'Sheet1', 'D6')) == (date(2026, 12, 15) - date(1899, 12, 30)).days
    assert cell(content, 'Sheet1', 'D20')  # the agent: the deal's owner


def test_K99_the_2_to_50_form_ticks_boxes_matrix_notes_and_additional_carriers(user, dated):
    ask(user, dated, 'aetna', 'guardian', 'trustmark', form='small_group', other_carriers='Oscar',
        notes='Renewal came in at +18%.', funding={'add': ['fully_insured']})  # fmt: skip
    request = ctx(dated)
    built = fill.build(request)
    sheet = 'RFP '
    assert cell(built.content, sheet, 'E40') == '1'  # fully insured
    assert cell(built.content, sheet, 'D31') == '1' and cell(built.content, sheet, 'E31') == '1'  # Aetna: med, den
    assert cell(built.content, sheet, 'D46') == '1'  # Guardian's dental box
    assert cell(built.content, sheet, 'D35') != '1'  # Florida Blue was not picked: Warner's own FALSE stays
    assert cell(built.content, sheet, 'C41').startswith('Notes: ')
    assert 'Renewal came in at +18%.' in cell(built.content, sheet, 'C41')
    assert cell(built.content, sheet, 'C60') == 'Additional Carriers: Oscar, Trustmark'
    found, _ = package.read_sheet(built.content, sheet)
    original, _ = package.read_sheet(fill.raw('small_group'), sheet)
    assert found.style_of('C41') != original.style_of('C41')  # the cell's own style plus wrap, as Alt+Enter leaves it


def test_K99_the_2_to_50_form_has_no_aso_box_and_the_check_says_so(api, user, dated):
    ask(user, dated, form='small_group', funding={'add': ['aso']})
    assert fill.funding_warnings(ctx(dated), 'small_group')
    report = api.get(f'/api/deals/{dated.id}/rfp/check/', {'file': 'form'}).json()
    assert any(problem['code'] == 'no_box' for problem in report['problems'])


def test_K42_the_form_with_the_census_inside_prints_the_universal_rows_up_to_500(user, dated):
    family(user, dated)
    request = ctx(dated)
    built = fill.build(request, 'simplified', census=True)
    layout = fill.census_layout('simplified')
    from rfp.formats import rows

    expected = rows.build(layout, request.people, request.lines, dated.effective_date)
    assert cell(built.content, 'Sheet1', 'B32') == expected.rows[0][0]
    request.people = crowd(501)
    capped = fill.build(request, 'large_group', census=True)
    assert any('room for 500' in text for text in capped.warnings)
    assert cell(capped.content, 'Census Template', f'B{7 + 499}') and not cell(
        capped.content, 'Census Template', 'B507'
    )


def test_K99_a_moved_label_fails_the_build_by_name():
    moved, _ = package.fill(fill.raw('simplified'), {'Sheet1': {'writes': {'C9': 'Something else'}}})
    with pytest.raises(FillError, match='C9'):
        fill.verify('simplified', moved)


def test_K46_the_variants_and_their_fit():
    small = {option['key']: option for option in maps.options('small')}
    assert small['simplified']['recommended'] and small['small_group']['applicable']
    assert not small['large_group']['applicable']
    assert all(fill.digest(key) == maps.SHA256[maps.VARIANTS[key]['file']] for key in maps.KEYS)


def _cover_text(api, deal):
    response = get(api, deal, 'cover')
    assert response.status_code == 200
    reader = PdfReader(io.BytesIO(body(response)))
    return len(reader.pages), ' '.join(page.extract_text() for page in reader.pages)


def test_K102_OQ65_the_cover_is_one_page_names_no_carrier_and_returns_to_the_owner(api, user, dated):
    user.email = 'owner@example.test'
    user.save(update_fields=['email'])
    ask(user, dated, 'aetna', 'cigna', route='direct', notes='Match the current deductibles.')
    pages, text = _cover_text(api, dated)
    assert pages == 1
    assert 'Request for Proposal' in text and 'Example Co.' in text and 'Match the current deductibles.' in text
    assert 'Aetna' not in text and 'Cigna' not in text
    assert 'owner@example.test' in text
    settings = AgencySettings.get()
    settings.rfp_return_email = 'quotes@agency.example.test'
    settings.save()
    assert 'quotes@agency.example.test' in _cover_text(api, dated)[1]
