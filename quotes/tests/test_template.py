"""The plan template round trip (plan.md §9.3)."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import load_workbook

from quotes import services
from quotes.models import Plan


def workbook_bytes(api, deal, line='medical'):
    response = api.get(f'/api/deals/{deal.id}/plans/template/?line={line}')
    assert response.status_code == 200
    return b''.join(response.streaming_content)


def edited(content, edits):
    workbook = load_workbook(io.BytesIO(content))
    for sheet, cell, value in edits:
        workbook[sheet][cell] = value
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def post(api, deal, content, dry_run=False):
    upload = SimpleUploadedFile('plans.xlsx', content)
    url = f'/api/deals/{deal.id}/plans/import/' + ('?dry_run=1' if dry_run else '')
    return api.post(url, {'file': upload}, format='multipart')


def cell_of(content, plan_id, key):
    ws = load_workbook(io.BytesIO(content))['Medical']
    row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == key)
    column = next(c for c in range(3, ws.max_column + 1) if ws.cell(4, c).value == plan_id)
    return ws.cell(row, column).coordinate


def test_export_edit_import_changes_only_the_edited_cell(api, deal, user):
    plan = services.create_plan(
        user,
        deal,
        line='medical',
        role='current',
        carrier='Aetna',
        name='HDHP',
        values={'deductible_single': '3300', 'pcp_copay': '25'},
    )
    content = workbook_bytes(api, deal)
    unchanged = post(api, deal, content, dry_run=True).json()
    assert unchanged['cells_changed'] == 0 and unchanged['update'] == 0
    before = Plan.objects.get(pk=plan.id).sources['pcp_copay']
    changed = edited(content, [('Medical', cell_of(content, plan.id, 'deductible_single'), 4000)])
    dry = post(api, deal, changed, dry_run=True).json()
    assert dry == {'create': 0, 'update': 1, 'cells_changed': 1, 'errors': []}
    assert Plan.objects.get(pk=plan.id).values['deductible_single'] == '3300'  # a dry run writes nothing
    result = post(api, deal, changed).json()
    assert result['cells_changed'] == 1
    plan.refresh_from_db()
    assert plan.values['deductible_single'] == '4000'
    assert plan.sources['deductible_single']['origin'] == 'import'
    assert plan.sources['deductible_single']['cell'].startswith('Medical!')
    assert plan.sources['pcp_copay'] == before
    assert deal.documents.filter(label='Plan template import').count() == 1


def test_reimporting_renewals_and_alternates_unchanged_changes_nothing(api, deal, user):
    current = services.create_plan(
        user, deal, line='medical', role='current', carrier='Aetna', name='PPO', values={'deductible_single': '1500'}
    )
    renewal = services.create_plan(
        user, deal, line='medical', role='renewal', carrier='Aetna', name='PPO', renews_id=current.id
    )
    services.create_plan(
        user, deal, line='medical', role='alternate', carrier='Cigna', name='OAP', replaces_ids=[current.id]
    )
    content = workbook_bytes(api, deal)
    edits_before = deal.activity.filter(area='quotes', action='updated').count()

    assert post(api, deal, content).json()['update'] == 0
    assert deal.activity.filter(area='quotes', action='updated').count() == edits_before

    changed = edited(content, [('Medical', cell_of(content, renewal.id, 'deductible_single'), 2000)])
    dry = post(api, deal, changed, dry_run=True).json()
    assert dry['update'] == 1
    assert post(api, deal, changed).json()['update'] == dry['update']


def test_new_plans_are_created_and_a_bad_cell_names_its_address(api, deal, user):
    content = workbook_bytes(api, deal)
    good = edited(content, [('Medical', 'C5', 'current'), ('Medical', 'C6', 'Cigna'), ('Medical', 'C7', 'LocalPlus')])
    assert post(api, deal, good, dry_run=True).json()['create'] == 1
    ws = load_workbook(io.BytesIO(good))['Medical']
    rate_row = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == 'rate_ee')
    bad = edited(good, [('Medical', f'C{rate_row}', 'abc')])
    body = post(api, deal, bad).json()
    assert body['errors'] and body['errors'][0]['cell'] == f'C{rate_row}'
    assert body['errors'][0]['message'] == 'Rate — EE takes a number, not "abc"'
    assert not Plan.objects.filter(deal=deal).exists()  # all-or-nothing


def test_unknown_field_and_unknown_sheet(api, deal):
    content = workbook_bytes(api, deal)
    workbook = load_workbook(io.BytesIO(content))
    workbook['Medical']['B12'] = 'not_a_field'
    workbook.create_sheet('Snacks')
    buffer = io.BytesIO()
    workbook.save(buffer)
    errors = post(api, deal, buffer.getvalue()).json()['errors']
    messages = [e['message'] for e in errors]
    assert 'unknown field "not_a_field"' in messages
    assert 'Sheet "Snacks" isn\'t a line of coverage' in messages


def test_formula_like_text_is_written_as_text(api, deal, user):
    services.create_plan(user, deal, line='medical', role='current', carrier='Aetna', name='=HYPERLINK("x")')
    ws = load_workbook(io.BytesIO(workbook_bytes(api, deal)))['Medical']
    cell = ws['C7']
    assert cell.data_type == 's' and cell.value.startswith('=')
