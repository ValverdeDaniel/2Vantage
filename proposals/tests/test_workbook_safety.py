"""The client spreadsheet's safety and its download (plan.md §9, §9.4; J24, J97, J104, J146, J151, J153; Q.8): text
that looks like a formula stays text, a formula is ours only, nothing a client must never see reaches any part of the
file, every rate basis prints its worked example (OQ103), and the draft download names itself and writes nothing."""

import datetime
import io

import openpyxl
import pytest

from conftest import make_deal
from deals.models import Activity
from proposals import services as proposal_services
from proposals.tests.test_workbook_recalc import RATE_BASES, _rate_bases_deal, _row_numbers, _tab_start
from proposals.workbook import build, grammar, write
from quotes import services
from quotes.models import Plan

pytestmark = pytest.mark.django_db
CANARIES = ('CANARY-STAR-REASON', 'CANARY-INTERNAL-NOTE', 'CANARY-LASER-4471', 'CANARY-MENTAL-HEALTH')


def _deal(user):
    deal = make_deal(user, name='Workbook safety (synthetic)', effective_date=datetime.date(2027, 1, 1))
    current = services.create_plan(
        user,
        deal,
        line='medical',
        role='current',
        carrier='=HYPERLINK("http://evil.example","x")',
        name='+1+1 HMO',
        values={
            'rate_ee': '500',
            'deductible_single': '1500',
            'telehealth': '@SUM(A1)',
            'mental_health_outpatient': CANARIES[3],
            'network': 'http://example.com/network',
        },
    )
    services.set_enrollment(user, deal, 'medical', plans=[{'id': current.id, 'enrollment': {'EE': 10}}])
    quote = services.create_plan(
        user,
        deal,
        line='medical',
        role='alternate',
        carrier='Cigna',
        name='-PPO 2000',
        values={'rate_ee': '480'},
        replaces_ids=[current.id],
    )
    services.star(user, deal, [quote.id], True, reason=CANARIES[0])
    Plan.objects.filter(pk=quote.id).update(notes=CANARIES[1])
    services.create_plan(
        user,
        deal,
        line='stop_loss',
        role='current',
        carrier='Swiss Re',
        name='Spec 50k',
        values={'sl_spec_rate': '85.20', 'sl_lasers': CANARIES[2]},
    )
    return deal


def _everything(data):
    """Every text the file holds: cells, sheet names, properties, validations, headers and footers."""
    loaded = openpyxl.load_workbook(io.BytesIO(data))
    found = list(loaded.sheetnames) + [str(v) for v in vars(loaded.properties).values() if v]
    for ws in loaded.worksheets:
        found += [str(cell.value) for row in ws.iter_rows() for cell in row if cell.value is not None]
        for rule in ws.data_validations.dataValidation:
            found += [str(rule.formula1), str(rule.prompt or ''), str(rule.error or '')]
        found += [str(part.text or '') for part in (ws.oddHeader.center, ws.oddFooter.center)]
    return found, loaded


def test_J153_text_that_looks_like_a_formula_or_a_link_stays_text(user):
    data = write.to_bytes(build.book(_deal(user)))
    _found, loaded = _everything(data)
    risky = ('=HYPERLINK("http://evil.example","x")', '+1+1 HMO', '-PPO 2000', '@SUM(A1)', 'http://example.com/network')
    seen = set()
    for ws in loaded.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and any(text in cell.value for text in risky):
                    assert cell.data_type == 's', (ws.title, cell.coordinate, cell.value)
                    assert cell.hyperlink is None, (ws.title, cell.coordinate)
                    seen.update(text for text in risky if text in cell.value)
    assert seen >= {'+1+1 HMO', '@SUM(A1)', 'http://example.com/network'}


def test_J153_a_formula_is_ours_only():
    with pytest.raises(grammar.Refused):
        grammar.check('=A1&"x"')
    with pytest.raises(grammar.Refused):
        grammar.check('=SUMPRODUCT(A1:A4,B1:B4)')
    with pytest.raises(grammar.Refused):
        grammar.check("='Elsewhere'!A1", sheets={'Medical All Plans'})
    with pytest.raises(grammar.Refused):
        grammar.check('=INDEX(A1:A3,1)')  # lookups only on the tabs that pass the file's own titles
    grammar.check('=IFERROR(INDEX(\'Medical All Plans\'!$B$5:$B$9,1),"")', sheets={'Medical All Plans'})


def test_Q8_J4_client_canaries_never_reach_the_workbook(user):
    data = write.to_bytes(build.book(_deal(user)))
    found, _loaded = _everything(data)
    for canary in CANARIES:
        assert not any(canary in text for text in found), canary


def test_OQ103_J151_every_rate_basis_prints_its_worked_example(user):
    book = build.book(_rate_bases_deal(user))
    for line, plans in RATE_BASES.items():
        title = next(t for t in book.titles() if t.lower().replace('-', ' ').startswith(_tab_start(line)))
        expected = [figure for _role, _rates, _enrollment, figure in plans]
        assert _row_numbers(book.by_title(title), 'Estimated Monthly Premium') == expected, line
        assert _row_numbers(book.by_title(title), 'Estimated Annual Premium') == [f * 12 for f in expected], line


def test_J146_markets_checked_prints_when_the_proposal_shows_it(user):
    deal = _deal(user)
    assert 'Markets Checked' not in build.book(deal).titles()
    proposal_services.set_config(user, deal, {'markets.on': True})
    book = build.book(deal)
    assert book.titles()[:2] == ['Cover', 'Markets Checked']
    texts = [cell.value for cell in book.by_title('Markets Checked').cells.values() if cell.kind == 'text']
    assert 'Current carrier' in texts and 'Cigna' in texts


def test_J24_J97_J104_the_draft_download_names_itself_and_writes_nothing(api, user):
    deal = _deal(user)
    before = Activity.objects.count()
    response = api.get(f'/api/deals/{deal.id}/proposal/files/xlsx/')
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert response['Content-Disposition'] == (
        'attachment; filename="Workbook safety synthetic - 2027 Benefits Proposal-DRAFT.xlsx"'
    )
    assert response['Cache-Control'] == 'private, no-store'
    loaded = openpyxl.load_workbook(io.BytesIO(b''.join(response.streaming_content)))
    assert loaded.sheetnames[0] == 'Cover'
    assert Activity.objects.count() == before


def test_J24_a_proposal_with_nothing_to_present_refuses_in_words(api, user):
    deal = make_deal(user, name='Nothing yet (synthetic)')
    response = api.get(f'/api/deals/{deal.id}/proposal/files/xlsx/')
    assert response.status_code == 409
    assert response.json()['detail'] == 'No plans on this proposal yet — add or star the plans to present first.'
