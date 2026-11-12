"""A call that ends without its usage is never recorded at $0 (plan.md §3.5, §10.3; D53; Daniel's $20 cap): Stop,
cancel or an error after sending charges at least the call's input estimate, or its whole reservation when even that
is unknown; a call never sent costs nothing (slice 24's fix of the stopped call the ledger settled at $0.00)."""

from decimal import Decimal
from types import SimpleNamespace

from ai import budget, calls, client, pricing
from ai.models import Call

PARAMS = {'model': pricing.SONNET, 'max_tokens': 32_000}


class Silent:
    """A transport whose call is stopped mid-stream before any usage came back (the parallel Runner's Abort)."""

    def send(self, params, *, key=None, on_event=None):
        raise calls.Aborted()


def planned(tokens):
    return calls.Planned(dict(PARAMS), ('test', 'x', 'p1'), tokens)


def test_D53_a_call_stopped_without_usage_is_charged_its_input_estimate(db):
    previous = client.install(Silent())
    try:
        done = calls.extract(planned(10_000), purpose='turn')
    finally:
        client.install(previous)
    row = Call.objects.get()
    assert isinstance(done.error, calls.Aborted) and row.status == Call.STOPPED
    assert row.cost_usd == pricing.cost(pricing.SONNET, {'input_tokens': 10_000}) > 0
    assert row.usage['input_tokens'] == 10_000 and row.usage['estimated'] == 'input'
    assert budget.total_spent() == row.cost_usd  # the cap counts it


def test_D53_with_no_estimate_either_a_sent_call_is_charged_its_reservation(db):
    row = calls.reserve(planned(0), purpose='turn')
    done = calls.settle(row, calls.Done(planned(0), error=calls.Aborted(), sent=True))
    row.refresh_from_db()
    assert done.cost == row.cost_usd == row.estimate_usd > 0


def test_D53_a_call_never_sent_costs_nothing_and_real_usage_is_kept(db):
    row = calls.reserve(planned(10_000), purpose='turn')
    assert calls.settle(row, calls.Done(planned(10_000)), stopped=True).cost == 0
    seen = client.Reply(model=pricing.SONNET, usage={'input_tokens': 3000, 'output_tokens': 40}, partial=True)
    row = calls.reserve(planned(10_000), purpose='turn')
    done = calls.settle(row, calls.Done(planned(10_000), reply=seen, sent=True), stopped=True)
    assert done.cost == pricing.cost(pricing.SONNET, {'input_tokens': 3000, 'output_tokens': 40}) < Decimal('0.03')


class _Stream:
    """The SDK's stream as Live reads it: a message_start with its usage, then text deltas."""

    def __init__(self):
        usage = SimpleNamespace(
            input_tokens=4000, output_tokens=1, cache_creation_input_tokens=0, cache_read_input_tokens=6000
        )
        start = SimpleNamespace(type='message_start', message=SimpleNamespace(model=pricing.SONNET, usage=usage))
        delta = SimpleNamespace(type='content_block_delta', delta=SimpleNamespace(text='x' * 30))
        self.events = [start, delta, delta]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        return iter(self.events)


def test_D53_live_keeps_what_a_call_used_when_stop_aborts_its_stream(db):
    live = client.Live('sk-test-not-sent')
    live._client = SimpleNamespace(messages=SimpleNamespace(stream=lambda **params: _Stream()))
    previous = client.install(live)

    def abort():
        raise calls.Aborted()

    try:
        done = calls.extract(planned(20_000), purpose='turn', on_event=abort)
    finally:
        client.install(previous)
    row = Call.objects.get()
    assert row.usage['input_tokens'] == 4000 and row.usage['cache_read_input_tokens'] == 6000  # the real input
    assert done.cost == row.cost_usd > 0 and row.status == Call.STOPPED
