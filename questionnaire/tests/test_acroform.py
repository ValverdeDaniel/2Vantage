"""Warner's form and the SIIA disclosure, filled into their own AcroForm fields (G59): values read back with pypdf,
Warner's "No" ticks its own box, the typed names sit in the /Sig rectangles with their dates, Warner's detail lines
print on an attachment, a filled row past the paper's last row prints nowhere, and a blank missing a field fails."""

import copy

import pytest

from questionnaire import forms, services
from questionnaire.check import problems
from questionnaire.models import Questionnaire
from questionnaire.pdf import acroform, build, fonts, printed

from .pdfs import drawn, fields, placed, reader
from .world import make_world

pytestmark = pytest.mark.django_db
SIIA, WP = 'stop_loss_siia', 'wp_lg'


@pytest.fixture
def stop_loss(user):
    deal = make_world(user, lines=('medical', 'stop_loss'))
    services.choose_form(user, deal.id, 'stop_loss_disclosure', SIIA)
    return deal


@pytest.fixture
def warner(user):
    deal = make_world(user)
    services.choose_form(user, deal.id, 'medical_questionnaire', WP)
    return deal


def risk_rows(deal):
    return [row['id'] for row in Questionnaire.objects.get(deal=deal, form=SIIA).rows['risks']]


def test_G59_the_disclosure_reads_back_from_its_own_fields(user, stop_loss):
    services.set_answers(user, stop_loss.id, SIIA, {'no_risks': 'No', 'claims_admin': 'Example TPA'})
    services.add_row(user, stop_loss.id, SIIA, 'risks')
    _blank, second = risk_rows(stop_loss)
    services.set_answers(user, stop_loss.id, SIIA, {
        f'risks.{second}.risk_identifier': 'M-1001', f'risks.{second}.dob': '1980-02-03',
        f'risks.{second}.coverage_status': 'COBRA', f'risks.{second}.expenses_incurred': '125000',
        f'risks.{second}.diagnosis': 'Example diagnosis',
    })  # fmt: skip
    found = fields(build.build(stop_loss, SIIA))
    assert found['Plan Sponsor'] == 'Example Fabrication LLC' and found['Claims Administrator'] == 'Example TPA'
    # the first filled risk takes the paper's first row; the letter the paper's column takes; money as written
    assert found['Risk Identifier_1'] == 'M-1001' and found['DOB_1'] == '02/03/1980'
    assert found['Active, COBRA, Retiree, or Termed_1'] == 'C'
    assert found['Expenses Incurred This Plan Year_1'] == '125,000'
    assert not found.get('Risk Identifier_2')


def test_G59_G53_the_typed_names_and_dates_after_signing(user, stop_loss):
    services.set_answers(user, stop_loss.id, SIIA, {'no_risks': 'Yes'})
    unsigned = build.build(stop_loss, SIIA)
    assert drawn(unsigned, fonts.DRAFT_NOTE)
    services.sign(user, stop_loss.id, SIIA, 'officer', 'Pat Sample', authorized=True)
    services.sign(user, stop_loss.id, SIIA, 'agent', 'Dana Agent')
    data = build.build(stop_loss, SIIA)
    found = fields(data)
    assert found['Date'] and found['Date_3'] and not found.get('Date_2')
    rects = acroform.sig_rects(reader(data))
    page, (x0, y0, x1, y1) = rects['Signature']
    hits = [(x, y) for x, y, text, _f in placed(reader(data).pages[page]) if text == 'Pat Sample']
    assert any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in hits)
    assert not drawn(data, fonts.DRAFT_NOTE)


def test_G59_warners_no_ticks_its_own_box_and_its_detail_prints_on_an_attachment(user, warner):
    services.set_answers(user, warner.id, WP, {'q1_hospitalized': 'No', 'q2_disabled': 'Yes',
                                               'medical_detail': 'Example detail line'})  # fmt: skip
    data = build.build(warner, WP)
    found = fields(data)
    assert found['Check Box 8'] not in (None, '/Off') and found['Check Box 7'] in (None, '/Off')  # q1: No
    assert found['Check Box 9'] not in (None, '/Off') and found['Check Box 10'] in (None, '/Off')  # q2: Yes
    assert found['Text Field 1'] == 'Example Fabrication LLC'
    assert found['Text Field 27'] == 'BlueOptions 1'  # the current plan's name in option 1 (G134)
    pages = reader(data).pages
    assert len(pages) == 2 and 'Example detail line' in pages[1].extract_text()


def test_G59_warners_history_rows_fill_its_three_paper_rows(user, warner):
    for _ in range(2):
        services.add_row(user, warner.id, WP, 'carriers')
    rows = [row['id'] for row in Questionnaire.objects.get(deal=warner, form=WP).rows['carriers']]
    services.set_answers(user, warner.id, WP, {f'carriers.{row}.carrier': f'Carrier {n}' for n, row in enumerate(rows)})
    found = fields(build.build(warner, WP))
    assert [found[f'Text Field {n}'] for n in (18, 19, 20)] == ['Carrier 0', 'Carrier 1', 'Carrier 2']


def test_G59_G64_a_filled_row_past_the_papers_last_row_prints_nowhere_and_the_check_says_so():
    form = forms.FORMS[WP]
    rows = {'carriers': [(n, {'carrier': f'Carrier {n}'}) for n in range(1, 5)]}
    found = printed.Printed(form, {}, rows, None, None, 'Example Co')
    assert acroform.unprinted(form, form['acroform'], found)['dropped'] == {'carriers': 1}
    said = problems.output(form, found, None, fix=None)
    assert [p['code'] for p in said] == ['not_printed'] and said[0]['count'] == 1
    assert 'Carrier 4' not in said[0]['text']  # rows by number, never an answer


def test_G59_a_blank_missing_a_mapped_field_fails_loudly(user, stop_loss, monkeypatch):
    drifted = copy.deepcopy(forms.FORMS[SIIA])
    drifted['acroform']['scalars']['plan_sponsor'] = 'Plan Sponsor (renamed)'
    monkeypatch.setitem(forms.FORMS, SIIA, drifted)
    with pytest.raises(acroform.AcroFormError, match='no longer matches'):
        build.build(stop_loss, SIIA)


def test_G59_every_mapped_field_exists_in_the_bundled_blanks():
    for key in (SIIA, WP):
        form = forms.FORMS[key]
        names = set(reader(forms.asset_path(form['acroform']['pdf']).read_bytes()).get_fields())
        assert set(acroform.mapped_names(form, form['acroform'])) <= names
