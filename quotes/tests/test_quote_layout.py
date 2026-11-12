"""The printed table of a scanned quote (plan.md §6.7, §7.8, O.3.5; Q.9 row 21; D66, D73, E42, E94, F42): written when
GD3's renewal packet lands, in the file's column order with its printed rows; rows that fill no field keep their
printed text and never become values; none for a PHI kind; replaced by a re-read and put back by Undo. The read is
replayed by the fake client; each test builds its own GD3."""

import copy
import hashlib
from types import SimpleNamespace

import pytest

from ai import client, read_files
from ai import services as ai
from ai.services.landing import UndoRefused
from deals.models import Activity
from documents.kinds import PHI_KINDS
from documents.models import Document
from documents.services import upload
from quotes import fields
from quotes import services as plan_services
from quotes.models import Plan, QuoteLayout
from quotes.reader import READS, corpus, printed

pytestmark = pytest.mark.django_db

D, F = 'BlueOptions PPO 2500', 'BlueCare HMO 1500'
CHIRO = 'Chiropractic visits'


@pytest.fixture
def packet(quote_first, gd3_packet_answer, fake_claude):
    deal = quote_first.built.deal
    document = Document.objects.get(deal=deal, kind='renewal')
    with document.file.open('rb') as handle:
        raw = handle.read()
    answer, label = gd3_packet_answer
    key = ('quotes', hashlib.sha256(raw).hexdigest()[:16], label)
    fake_claude.record(key, answer)
    return SimpleNamespace(deal=deal, document=document, answer=answer, key=key, fake=fake_claude)


def read(user, packet, answer=None):
    if answer is not None:
        packet.fake.record(packet.key, answer)
    job, _created = ai.start_read(user, packet.deal, [packet.document.id])
    job.refresh_from_db()
    return job


def chiro_printed(answer, text):
    """The packet's answer with the row that fills no field printing other words (a carrier's corrected sheet)."""
    answer = copy.deepcopy(answer)
    row = next(row for row in answer['lines'][0]['rows'] if row['label'] == CHIRO)
    for cell in row['cells']:
        cell['value'] = text
    return answer


def printed_rows(answer):
    """The packet's printed rows in printed order, from the perfect read: (label, fills a field); a row the read
    splits into two fields (a deductible's halves) is one printed row."""
    out = []
    for row in answer['lines'][0]['rows']:
        if not (out and row['key'] and out[-1] == (row['label'], True)):
            out.append((row['label'], bool(row['key'])))
    return out


def layout_of(packet):
    return QuoteLayout.objects.get(document=packet.document, line='medical')


def test_D66_GD3_use_this_scan_keeps_the_packet_table_in_printed_order(user, packet):
    job = read(user, packet)
    _job, landed = ai.apply(user, job.id)

    layout = layout_of(packet)
    names = {plan.id: (plan.role, plan.name) for plan in Plan.objects.filter(deal=packet.deal)}
    assert [names[column['plan']] for column in layout.columns] == [
        ('current', D),
        ('renewal', D),
        ('current', F),
        ('renewal', F),
    ]
    assert [column['col'] for column in layout.columns] == sorted(column['col'] for column in layout.columns)
    assert [column['head'] for column in layout.columns] == [D, D, F, F]
    assert [(row['label'], bool(row['keys'])) for row in layout.rows] == printed_rows(packet.answer)
    chiro = next(row for row in layout.rows if row['label'] == CHIRO)
    assert chiro == {'label': CHIRO, 'keys': [], 'printed': ['20 a year'] * 4}
    assert (layout.job_id, layout.where) == (job.id, {'page': 2})
    row = Activity.objects.get(pk=landed['activity_id'])
    assert {'t': f'layout:{packet.document.id}:medical', 'k': {'layout.job': [None, job.id]}} in row.changes


def test_D66_rows_that_fill_no_field_never_become_values(user, packet):
    job = read(user, packet)
    ai.apply(user, job.id)

    for plan in Plan.objects.filter(deal=packet.deal, read_ref__job=job.id):
        assert set(plan.values) <= set(fields.keys_for(plan.line))
        assert '20 a year' not in plan.values.values()


def test_D66_a_phi_kind_keeps_no_printed_text(user, packet):
    Document.objects.filter(pk=packet.document.pk).update(kind=sorted(set(PHI_KINDS) & set(READS))[0])
    job = read(user, packet)
    ai.apply(user, job.id)

    rows = layout_of(packet).rows
    assert [row['label'] for row in rows if not row['keys']] == [CHIRO]
    assert not any('printed' in row for row in rows)


def test_E42_a_file_filed_as_phi_after_its_read_shows_no_printed_text(api, user, packet):
    ai.apply(user, read(user, packet).id)
    Document.objects.filter(pk=packet.document.pk).update(kind=sorted(set(PHI_KINDS) & set(READS))[0])

    body = api.get(f'/api/deals/{packet.deal.id}/plans/as-quoted/?document={packet.document.id}').json()

    assert next(row for row in body['rows'] if row['label'] == CHIRO)['printed'] == [''] * 4


def test_F42_E42_as_quoted_lists_the_files_and_serves_one_table(api, user, packet):
    base = f'/api/deals/{packet.deal.id}/plans/as-quoted/'
    assert api.get(base).json() == {'files': []}
    ai.apply(user, read(user, packet).id)

    files = api.get(base).json()['files']
    assert [(entry['document'], entry['line'], entry['plans']) for entry in files] == [
        (packet.document.id, 'medical', 4)
    ]
    body = api.get(f'{base}?document={packet.document.id}&line=medical').json()
    plans = {plan.id: plan.name for plan in Plan.objects.filter(deal=packet.deal)}
    assert [plans[column['plan']] for column in body['columns']] == [D, D, F, F]
    assert [(row['label'], bool(row['keys'])) for row in body['rows']] == printed_rows(packet.answer)
    assert (body['where'], body['left_out'], body['line_label']) == ({'page': 2}, 0, 'Medical')
    assert api.get(f'{base}?document=x').status_code == 400
    assert api.get(f'{base}?document={packet.document.id}&line=nope').status_code == 400
    assert api.get(f'{base}?document={packet.document.id}&line=dental').status_code == 404
    assert api.get(f'{base}?document=999999999').status_code == 404


def test_F42_a_plan_removed_since_leaves_its_column_out(api, user, packet):
    ai.apply(user, read(user, packet).id)
    removed = layout_of(packet).columns[1]['plan']
    plan_services.delete_plans(user, packet.deal, [removed])

    body = api.get(f'/api/deals/{packet.deal.id}/plans/as-quoted/?document={packet.document.id}').json()

    assert removed not in [column['plan'] for column in body['columns']] and body['left_out'] == 1
    chiro = next(row for row in body['rows'] if row['label'] == CHIRO)
    assert chiro['printed'] == ['20 a year'] * 3


def test_D73_undo_this_run_takes_the_table_off(user, packet):
    job = read(user, packet)
    ai.apply(user, job.id)

    ai.undo(user, job.id)

    assert not QuoteLayout.objects.filter(document=packet.document).exists()


def test_D66_an_unchanged_reread_writes_nothing_and_a_changed_one_replaces_the_table(user, packet):
    first = read(user, packet)
    ai.apply(user, first.id)
    written = layout_of(packet).written_at
    rows = Activity.objects.filter(deal=packet.deal).count()

    same = read(user, packet)
    _same, landed = ai.apply(user, same.id)
    assert (landed['activity_ids'], layout_of(packet).written_at) == ([], written)
    assert Activity.objects.filter(deal=packet.deal).count() == rows

    again = read(user, packet, chiro_printed(packet.answer, '30 a year'))
    _again, landed = ai.apply(user, again.id)
    layout = layout_of(packet)
    assert next(row for row in layout.rows if row['label'] == CHIRO)['printed'] == ['30 a year'] * 4
    assert (layout.job_id, landed['summary']) == (again.id, 'the file’s printed table')
    assert Activity.objects.get(pk=landed['activity_id']).summary == 'Used Claude’s read: the file’s printed table'

    ai.undo(user, again.id)  # the first read's table comes back

    layout = layout_of(packet)
    assert next(row for row in layout.rows if row['label'] == CHIRO)['printed'] == ['20 a year'] * 4
    assert (layout.job_id, layout.written_at) == (first.id, written)


def test_D73_undo_refuses_when_a_later_read_replaced_the_table_and_undo_anyway_leaves_it(user, packet):
    first = read(user, packet)
    _first, landed = ai.apply(user, first.id)
    again = read(user, packet, chiro_printed(packet.answer, '30 a year'))
    ai.apply(user, again.id)

    with pytest.raises(UndoRefused) as refused:
        ai.undo(user, first.id)
    assert 'printed table' in refused.value.sentence

    ai.undo(user, first.id, force=True)
    assert not Plan.objects.filter(id__in=landed['created']).exists()
    assert layout_of(packet).job_id == again.id


def test_E94_a_landed_read_keeps_the_printed_page_numbers(user, quote_first, fake_claude):
    deal = quote_first.built.deal
    table = corpus.table(
        'medical',
        'Harbor Mutual',
        '2027 quote',
        [
            corpus.medical(
                'Harbor PPO 1000',
                'quote',
                {'deductible_single': '1000'},
                ('500', '1000', '900', '1500'),
                carrier='Harbor Mutual',
            )
        ],  # fmt: skip
    )
    raw = printed_pdf_numbered_from_the_table(table)
    document = upload(
        user,
        deal,
        _file('Harbor quote (synthetic).pdf', raw),
        {'kind': 'quote', 'role': 'alternates', 'carrier': 'Harbor Mutual', 'lines': ['medical']},
    )
    parts, _left_out, _failure = read_files.plan(
        read_files.FileIn(id=document.id, raw=raw, extension='.pdf'), max_tokens=client.MAX_TOKENS
    )
    fake_claude.record(
        ('quotes', hashlib.sha256(raw).hexdigest()[:16], parts[0].label), printed.answer([table], pages={0: 2})
    )
    job, _created = ai.start_read(user, deal, [document.id])
    job.refresh_from_db()

    ai.apply(user, job.id)

    document.refresh_from_db()
    assert document.page_labels == {'2': '1'}
    assert QuoteLayout.objects.get(document=document).where == {'page': 2}


def printed_pdf_numbered_from_the_table(table):
    """A cover letter with no number, then the table on PDF page 2 printing "Page 1 of 1" (a packet numbered anew)."""
    from synthetic_files import pdf

    lines = [(40, 720, f'{table["title"]}: plan options', 12)]
    y = 690
    for label, _key, values in table['rows']:
        lines.append((40, y, label, 8))
        lines += [(220, y, str(value), 8) for value in values]
        y -= 14
    lines.append((520, 16, 'Page 1 of 1', 7))
    return pdf([[(40, 700, 'Dear benefits partner, enclosed are the plan options and rates.', 11)], lines])


def _file(name, raw):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(name, raw)


def test_Q3_4_as_quoted_reads_the_same_queries_at_one_and_ten_tables(api, user, deal):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    from deals import clock

    plan = Plan.objects.create(deal=deal, line='medical', role='alternate', carrier='Harbor Mutual', name='PPO 1000')

    def tables(count):
        for number in range(count):
            document = Document.objects.create(
                deal=deal, file=f'deals/{deal.id}/q{number}.pdf', original_name=f'Quote {number} (synthetic).pdf',
                kind='quote',
            )  # fmt: skip
            QuoteLayout.objects.create(
                deal=deal, document=document, line='medical', where={'page': 1}, written_at=clock.now(),
                columns=[{'col': 0, 'plan': plan.id, 'head': plan.name}],
                rows=[{'label': 'Chiro', 'keys': [], 'printed': ['20/yr']}, {'label': 'EE', 'keys': ['rate_ee']}],
            )  # fmt: skip
        return document

    def queries(path):
        with CaptureQueriesContext(connection) as captured:
            assert api.get(f'/api/deals/{deal.id}/plans/as-quoted/{path}').status_code == 200
        return len(captured.captured_queries)

    one = tables(1)
    small = (queries(''), queries(f'?document={one.id}'))
    ten = tables(9)
    assert (queries(''), queries(f'?document={ten.id}')) == small
