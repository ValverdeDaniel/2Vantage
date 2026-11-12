"""Claude's mapping assist (plan.md §4.8, §5.3.2 step 4, §10.4, §10.8, Q.6; C14, D109; slice 51), and the census
reader behind the PHI-gate switch (§11.4 item 7). The fake client records every request, so the tests read exactly
what would have left for Claude: headers and value shapes, never a member's value."""

import hashlib
import json

import pytest
from rest_framework.exceptions import ValidationError

from ai import kinds, registry, services
from ai.services.jobs import PHI_OFF
from census import reader as census_reader
from census.models import CensusImport, Member
from census.reader import assist
from documents.tests.helpers import stored

from .helpers import xlsx

HEADERS = ['Emp ID', 'Relationship', 'Given', 'Surname', 'Born', 'Sex', 'Postal', 'Weekly Hrs', 'Med Plan', 'Cov Lvl']
PEOPLE = [
    ['E9001', 'Employee', 'Zephyrine', 'Quillonbeck', '07/19/1983', 'F', '33601', 40, 'Gold PPO', 'FAM'],
    ['E9001', 'Spouse', 'Marisolde', 'Quillonbeck', '02/02/1984', 'F', '', '', '', ''],
    ['E9002', 'Employee', 'Oskar', 'Pembleton', '03/03/1975', 'M', '33602', 32, 'Gold PPO', 'EE'],
]
VALUES = ('Zephyrine', 'Quillonbeck', 'Marisolde', 'Pembleton', 'E9001', '07/19/1983', '1983', '33601', 'Gold PPO')
ANSWER = {
    'columns': [
        {'column': 4, 'field': 'dob', 'confidence': 0.9},
        {'column': 9, 'field': 'medical_tier', 'confidence': 0.85},
        {'column': 2, 'field': 'first_name', 'confidence': 0.9},
        {'column': 3, 'field': 'gender', 'confidence': 0.9},  # not asked about: Surname is mapped
        {'column': 7, 'field': 'zip', 'confidence': 0.9},  # Postal holds zip already
    ]
}


def _sheet_read(user, deal, fake, answer=ANSWER):
    raw = xlsx([HEADERS, *PEOPLE])
    document = stored(user, deal, 'census (synthetic).xlsx', raw, kind='census')
    fake.record(('census_assist', hashlib.sha256(raw).hexdigest()[:16], 'columns'), answer)
    job, _ = services.start_read(user, deal, [document.id], target='census')
    job.refresh_from_db()
    return job, document


def test_D109_the_mapping_assist_sends_headers_and_value_shapes_never_a_value(user, deal, fake_claude):
    job, _document = _sheet_read(user, deal, fake_claude)
    assert [entry['key'][0] for entry in fake_claude.log] == ['census_assist']  # Claude never read the rows
    sent = json.dumps(fake_claude.log[0]['params'])
    assert not [value for value in VALUES if value.lower() in sent.lower()]
    asked = fake_claude.log[0]['params']['messages'][0]['content'][0]['text']
    assert '"Cov Lvl": 3 letters (1 of 3), 2 letters (1 of 3)' in asked and '"Born": a date (3 of 3)' in asked
    assert 'Map these columns: 2, 4, 7, 9' in asked
    assert job.status == kinds.DONE and job.result['items'][0]['assisted'] == 3
    assert not any(json.dumps(job.result).lower().count(value.lower()) for value in VALUES)


def test_D109_the_assist_proposes_only_for_columns_left_and_never_replaces_the_offline_mapper(user, deal, fake_claude):
    job, _document = _sheet_read(user, deal, fake_claude)
    imp = CensusImport.objects.get(job=job)
    by_column = {item['column']: item for item in imp.mapping}
    assert by_column[4]['field'] == 'dob' and by_column[4]['assist'] and by_column[4]['low']
    assert by_column[9]['field'] == 'medical_tier' and by_column[9]['confidence'] == assist.ASSISTED
    assert by_column[3]['field'] == 'last_name' and not by_column[3].get('assist')  # mapped exactly: never asked
    assert by_column[7]['field'] == 'hours_per_week'  # Claude's zip is Postal's already
    assert imp.status == CensusImport.PROPOSED and Member.all_objects.filter(deal=deal).count() == 0


def test_D109_a_file_already_waiting_keeps_the_persons_choices_and_the_assist_maps_the_rest(user, deal, fake_claude):
    from census import services as census

    raw = xlsx([HEADERS, *PEOPLE])
    document = stored(user, deal, 'census (synthetic).xlsx', raw, kind='census')
    waiting = census.create_import(user, deal.id, document.id)
    census.update_import(user, waiting.id, {'mapping': [{'column': 7, 'field': ''}]})  # the person drops Weekly Hrs
    fake_claude.record(('census_assist', hashlib.sha256(raw).hexdigest()[:16], 'columns'), {'columns': []})
    job, _ = services.start_read(user, deal, [document.id], target='census')
    imp = CensusImport.objects.get(job=job)
    waiting.refresh_from_db()
    assert waiting.status == CensusImport.DISCARDED and imp.status == CensusImport.PROPOSED
    assert next(item for item in imp.mapping if item['column'] == 7)['field'] == ''
    assert 'Map these columns: 2, 4, 7, 9' in fake_claude.log[0]['params']['messages'][0]['content'][0]['text']


def test_D109_shapes_say_what_a_value_looks_like_in_words():
    assert assist.shape('539-26-8817') == '9 digits with dashes or spaces' and assist.shape('07/19/1983') == 'a date'
    assert assist.shape('EE') == '2 letters' and assist.shape('Zephyrine') == 'a word'
    assert assist.shape('***-**-8817') == 'a masked number ending in 4 digits' and assist.shape('') == 'blank'
    assert assist.shape('$52,000.00') == 'an amount' and assist.shape('Mary Ann') == 'text, 2 words'


def test_D109_a_failed_assist_leaves_the_offline_mapping(user, deal, fake_claude):
    raw = xlsx([HEADERS, *PEOPLE])
    document = stored(user, deal, 'census (synthetic).xlsx', raw, kind='census')
    fake_claude.record(('census_assist', hashlib.sha256(raw).hexdigest()[:16], 'columns'), None, fault='refusal')
    job, _ = services.start_read(user, deal, [document.id], target='census')
    job.refresh_from_db()
    imp = CensusImport.objects.get(job=job)
    assert not any(item.get('assist') for item in imp.mapping) and job.status == kinds.DONE
    assert any('could not propose' in finding['text'] for finding in job.result['findings'])


@pytest.fixture
def switch_off(settings):
    settings.AI_PHI_READERS = False
    registry.readers.pop('census', None)
    yield
    settings.AI_PHI_READERS = True
    census_reader.register()


def test_PHI7_the_census_reader_waits_for_the_phi_gate_switch(user, deal, fake_claude, switch_off):
    assert census_reader.register() is False and 'census' not in registry.readers
    document = stored(user, deal, 'census (synthetic).xlsx', xlsx([HEADERS, *PEOPLE]), kind='census')
    with pytest.raises(ValidationError) as refused:
        services.start_read(user, deal, [document.id], target='census')
    assert refused.value.detail['target'] == [PHI_OFF]
    sent, not_read = services.start_send(user, deal, [document.id])
    assert sent == [] and not_read == [document.id] and fake_claude.log == []
    from ai.selectors import meta

    assert meta()['phi_readers'] is False and 'census' not in meta()['tabs']['census']


def test_PHI7_with_the_switch_on_the_census_reader_is_registered(settings):
    settings.AI_PHI_READERS = True
    assert census_reader.register() is True and registry.readers['census'].must_review
    assert 'census' in registry.readers['census'].kinds and kinds.READ in kinds.LANE_OF
