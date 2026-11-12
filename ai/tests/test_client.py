"""The Claude client (plan.md §10.3, §3.5; D.6, OQ29; slice 18): Messages API only, structured output, no key no
client, stop reasons turned into errors. No test reaches the network: settings_test blanks the key."""

import json

import pytest

from ai import client, codes


def test_OQ29_no_client_without_the_setting_even_with_the_variable_set(settings, monkeypatch):
    settings.ANTHROPIC_API_KEY = ''
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-not-a-real-key')
    previous = client.install(None)
    try:
        assert not client.available()
        with pytest.raises(client.NoKey):
            client.transport()
    finally:
        client.install(previous)


def test_D6_a_request_is_one_structured_output_call_with_adaptive_thinking():
    params = client.request(
        model='claude-sonnet-5-5',
        system='Read.',
        content=[{'type': 'text', 'text': 'x'}],
        schema={'type': 'object'},
        effort='high',
    )
    assert params['max_tokens'] == 128_000
    assert params['thinking'] == {'type': 'adaptive'}
    assert params['output_config'] == {
        'effort': 'high',
        'format': {'type': 'json_schema', 'schema': {'type': 'object'}},
    }
    assert params['system'][0]['cache_control'] == {'type': 'ephemeral'}
    assert [message['role'] for message in params['messages']] == ['user']  # no prefill
    assert not {'temperature', 'top_p', 'top_k', 'tools', 'tool_choice', 'betas', 'extra_headers'} & set(params)


def test_D50_D91_stop_reasons_become_errors_that_keep_what_was_used():
    used = {'input_tokens': 10, 'output_tokens': 128_000}
    with pytest.raises(client.Truncated) as cut:
        client.check(client.Reply('claude-sonnet-5-5', used, 'max_tokens', '{"lines": ['))
    assert cut.value.seen.usage == used
    with pytest.raises(client.Refused):
        client.check(client.Reply('claude-sonnet-5-5', used, 'refusal', ''))
    with pytest.raises(client.CallFailed):
        client.check(client.Reply('claude-sonnet-5-5', used, 'end_turn', 'not json'))
    assert client.check(client.Reply('claude-sonnet-5-5', used, 'end_turn', json.dumps({'n': 1}))) == {'n': 1}


@pytest.mark.parametrize(
    ('printed', 'parsed'),
    [
        ('108114-00, 01', ['108114-00', '108114-01']),
        ('108114-00; -01', ['108114-00', '108114-01']),
        ('108114-00 / 108114-01', ['108114-00', '108114-01']),
        ('10811406 ACTIVE / 10811407 COBRA', ['10811406', '10811407']),
        ('Group No. 5906', ['5906']),
    ],
)
def test_F143_codes_fold_every_way_a_carrier_prints_them(printed, parsed):
    assert codes.parse(printed) == parsed


def test_F143_only_strong_codes_name_one_plan():
    assert codes.overlap('108114-06', ['10811406'])
    assert not codes.overlap('5906', ['5906'])  # Blue Cross reissues four-digit numbers (D-049)
    assert codes.number_parts('05182 / 05183') == {'05182', '05183'}
    assert codes.number_parts('TBD') == set()
