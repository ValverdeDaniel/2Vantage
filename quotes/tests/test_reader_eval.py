"""The Eval lane's scoring (plan.md §12.8; Q.6; slice 18), run here on the fake client: a perfect read of the corpus
meets every threshold, and each named fault costs the metric it should. The live lane is `manage.py reader_eval`."""

import hashlib

from ai import eval as reader_eval
from ai import registry
from quotes.reader import corpus, faults

METRICS = ('plans_precision', 'plans_recall', 'roles', 'order', 'rates_exact', 'design')


def _record(fake, case, answer=None):
    fake.record(('quotes', hashlib.sha256(case.raw).hexdigest()[:16], case.range), answer or case.answer)


def _run(cases):
    return reader_eval.run(registry.readers['quotes'], cases, model='claude-sonnet-5-5', effort='high')


def test_Q6_a_perfect_read_of_the_corpus_scores_full_marks(db, fake_claude):
    cases = corpus.cases()
    for case in cases:
        _record(fake_claude, case)
    report = _run(cases)
    assert set(report['sets']) == {corpus.TUNING, corpus.HELD_OUT}
    for totals in report['sets'].values():
        assert all(totals['metrics'][name] == 1.0 for name in METRICS), totals['metrics']
        assert totals['metrics']['rates_wrong_unflagged'] == 0.0 and totals['metrics']['written_on_blank'] == 0.0
    assert not [miss for miss in reader_eval.check(report) if 'cost' not in miss]
    assert all(set(row) >= {'counts', 'cost_usd', 'estimate_usd'} for row in report['cases'])  # counts, no values


def test_Q6_each_fault_costs_its_metric(db, fake_claude):
    renewal, quotes = corpus.renewal_two_current(), corpus.quotes_three()
    _record(fake_claude, renewal, faults.faulty(renewal, 'missed_link'))
    _record(fake_claude, quotes, faults.faulty(quotes, 'starred_rate'))
    tuning = _run([renewal, quotes])['sets'][corpus.TUNING]['metrics']
    assert tuning['roles'] < 1.0 and tuning['rates_exact'] < 1.0
    _record(fake_claude, quotes, faults.faulty(quotes, 'invented_plan'))
    assert _run([quotes])['sets'][corpus.TUNING]['metrics']['plans_precision'] < 1.0
    _record(fake_claude, quotes, faults.faulty(quotes, 'blank_cell'))
    assert _run([quotes])['sets'][corpus.TUNING]['metrics']['rates_exact'] < 1.0


def test_Q6_the_corpus_is_the_same_bytes_every_run():
    first, second = corpus.cases(), corpus.cases()
    assert [case.raw for case in first] == [case.raw for case in second]
    assert {case.set for case in first} == {corpus.TUNING, corpus.HELD_OUT}


def test_Q6_D66_a_read_that_drops_a_row_that_fills_no_field_loses_the_printed_order(db, fake_claude):
    renewal = corpus.renewal_two_current()
    answer = {**renewal.answer, 'lines': [dict(block) for block in renewal.answer['lines']]}
    block = answer['lines'][0]
    block['rows'] = [row for row in block['rows'] if row['key']]  # the unmapped printed rows left out
    _record(fake_claude, renewal, answer)
    report = _run([renewal])
    counts = report['cases'][0]['counts']
    assert (counts['rows_exact'], counts['order_exact']) == (0, 0)
    assert report['sets'][corpus.TUNING]['metrics']['order'] < 1.0
