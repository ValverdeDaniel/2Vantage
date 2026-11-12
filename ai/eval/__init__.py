"""The Eval lane (plan.md §12.8; Q.2, Q.6): live reads of a reader's synthetic corpus, scored against its keys.

`run(reader, cases, model=…, effort=…)` reads each case's file through the same planning and calls as a job
(`read_files.plan`, `reading.planned_call`, `calls.extract`; every call goes in the ledger as purpose `eval` and the
total cap holds), merges the answers with the reader's own `merge` and scores them with its `score`. The report holds
counts and rates only, never a value, a file's text or a name; `check(report)` lists Q.6's thresholds it misses.
Opt-in and paid: `manage.py reader_eval` runs it only when asked.
"""

from decimal import Decimal

from .. import budget, calls, client, read_files, reading

# Q.6: (metric, tuning, held-out, 'min' or 'max')
THRESHOLDS = [
    ('plans_precision', 1.0, 0.95, 'min'),
    ('plans_recall', 1.0, 0.95, 'min'),
    ('roles', 0.98, 0.98, 'min'),
    ('order', 1.0, 0.95, 'min'),
    ('rates_exact', 0.995, 0.995, 'min'),
    ('rates_wrong_unflagged', 0.002, 0.002, 'max'),
    ('design', 0.97, 0.97, 'min'),
    ('written_on_blank', 0.005, 0.005, 'max'),
]
COST_SPREAD = Decimal('0.30')  # the cost may differ from the estimate by 30% either way, never past the run's cap


def _rate(top, bottom):
    return round(top / bottom, 4) if bottom else 1.0


def metrics(counts):
    return {
        'plans_precision': _rate(counts['plans_matched'], counts['plans_found']),
        'plans_recall': _rate(counts['plans_matched'], counts['plans_key']),
        'roles': _rate(counts['roles_right'], counts['roles']),
        'order': _rate(counts['order_exact'], counts['order_cases']),
        'rates_exact': _rate(counts['rates_exact'], counts['rates']),
        'rates_wrong_unflagged': _rate(counts['rates_wrong_unflagged'], counts['rates']) if counts['rates'] else 0.0,
        'design': _rate(counts['design_right'], counts['design']),
        'written_on_blank': _rate(
            counts['written_on_blank'], counts['written_on_blank'] + counts['design'] + counts['rates']
        )
        if counts['written_on_blank']
        else 0.0,
    }


def read_case(reader, case, *, model, effort, on_call=None):
    """(merged, case report) for one case, read live (or through an installed fake)."""
    file = read_files.FileIn(
        id=case.name,
        raw=case.raw,
        extension=case.extension,
        kind=case.kind,
        role=case.role,
        carrier=case.carrier,
        lines=list(case.lines),
    )
    parts_plan, left_out, failure = read_files.plan(file, max_tokens=client.MAX_TOKENS)
    estimate = budget.run_estimate(model, parts_plan, reading.prompt_tokens(reader))
    note = reader.note(file, {'deal_lines': list(case.lines)})
    parts, failed, cost = [], [], Decimal(0)
    for part in parts_plan:
        planned = reading.planned_call(reader, file, part, note, model=model, effort=effort)
        done = calls.extract(planned, purpose='eval')
        cost += Decimal(done.cost or 0)
        if on_call:
            on_call(case, part, done)
        if done.error is None:
            parts.append((file, part, done.data))
        else:
            failed.append({'where': part.where(), 'reason': done.error.reason})
    merged = reader.merge(parts, [file])
    return merged, {
        'case': case.name,
        'set': case.set,
        'ranges': [part.label for part in parts_plan],
        'left_out_pages': sorted(left_out),
        'failed': failed + ([failure] if failure else []),
        'estimate_usd': f'{estimate:.4f}',
        'cost_usd': f'{cost:.4f}',
    }


def run(reader, cases, *, model, effort, on_call=None):
    """Read and score every case. {'model', 'cases': [...], 'sets': {set: {'counts', 'metrics', 'cost', ...}}}."""
    report = {'model': model, 'effort': effort, 'cases': [], 'sets': {}}
    for case in cases:
        merged, row = read_case(reader, case, model=model, effort=effort, on_call=on_call)
        row['counts'] = reader.score(case.key, merged)
        report['cases'].append(row)
        totals = report['sets'].setdefault(case.set, {'counts': {}, 'estimate_usd': Decimal(0), 'cost_usd': Decimal(0)})
        for key, value in row['counts'].items():
            totals['counts'][key] = totals['counts'].get(key, 0) + value
        totals['estimate_usd'] += Decimal(row['estimate_usd'])
        totals['cost_usd'] += Decimal(row['cost_usd'])
    for totals in report['sets'].values():
        totals['metrics'] = metrics(totals['counts'])
        totals['estimate_usd'] = f'{totals["estimate_usd"]:.4f}'
        totals['cost_usd'] = f'{totals["cost_usd"]:.4f}'
    return report


def check(report):
    """[sentence] for every threshold a set misses, and for a cost off its estimate by more than 30% (Q.6)."""
    misses = []
    for name, totals in report['sets'].items():
        for metric, tuning, held_out, way in THRESHOLDS:
            bar = tuning if name == 'tuning' else held_out
            value = totals['metrics'][metric]
            if (way == 'min' and value < bar) or (way == 'max' and value > bar):
                misses.append(f'{name}: {metric} {value} (needs {"at least" if way == "min" else "at most"} {bar})')
        estimate, cost = Decimal(totals['estimate_usd']), Decimal(totals['cost_usd'])
        if estimate and abs(cost - estimate) > estimate * COST_SPREAD:
            misses.append(f'{name}: cost ${cost:.4f} against an estimate of ${estimate:.4f} (more than 30% off)')
    for row in report['cases']:
        if Decimal(row['cost_usd']) > budget.run_cap():
            misses.append(f'{row["case"]}: cost ${row["cost_usd"]} over the run cap')
    return misses
