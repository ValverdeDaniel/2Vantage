"""The synthetic filled form for reader trials and its score (plan.md §12.8; G109; slice 52): the sample stamps onto the
carrier's blank, a perfect read of it (the fake client) is staged whole, and the score counts it right — never a
value in the score."""

import json

import pytest

from ai import read_files
from ai.services import start_read
from documents.tests.helpers import stored
from questionnaire import trials
from questionnaire.models import StagedRead

from .reader_world import key
from .world import make_world

pytestmark = pytest.mark.django_db


def _perfect(answer_key, pages):
    """Claude's answer for the sample, as the schema has it: every answer and row on the first page."""
    first = pages[0]
    rows = [
        {'block': block, 'page': first, 'values': [{'key': k, 'value': v, 'unsure': False} for k, v in row.items()]}
        for block, listed in answer_key['rows'].items()
        for row in listed
    ]
    answers = [{'key': k, 'value': v, 'page': first, 'unsure': False} for k, v in answer_key['answers'].items()]
    return {'answers': answers, 'rows': rows}


def test_G109_the_sample_form_read_whole_scores_every_answer_right(user, fake_claude):
    deal = make_world(user, plans=0)
    raw = trials.printed_sample()
    document = stored(user, deal, 'trial (synthetic).pdf', raw, kind='questionnaire')
    [file], _failed = read_files.from_documents([document])
    parts, _out, _failure = read_files.plan(file, max_tokens=128_000)
    answer_key = trials.key()
    for part in parts:
        fake_claude.record(key(raw, part.label), _perfect(answer_key, part.pages) if part is parts[0] else {})
    job, _ = start_read(user, deal, [document.id], target='questionnaire')
    staged = StagedRead.objects.get(job=job)
    score = trials.score(answer_key, staged.read)
    assert score['answers']['right'] == score['answers']['key'] and not score['answers']['wrong']
    assert all(block['exact'] == block['key'] for block in score['rows'].values())
    assert 'Example Trial' not in json.dumps(score) and 'Renal' not in json.dumps(score)  # counts only


def test_G109_the_sample_prints_its_answers_on_the_carrier_s_form():
    from io import BytesIO

    from pypdf import PdfReader

    text = ' '.join(page.extract_text() or '' for page in PdfReader(BytesIO(trials.printed_sample())).pages)
    assert 'Example Trial Fabrication LLC' in text and 'Renal Failure' in text and 'Riley Example' in text
