"""Per-plan results for a line, packages and the recommendation (plan.md §5.4, §5.5). Pure functions.

The rule that keeps totals honest is about people: a package's change against today is shown only when it covers
the same people as today, each counted once. Results hold the API's plain numbers (`math.plain`); every sum and
comparison of enrollment is made in Decimal.
"""

from . import math as m


def _people(result):
    figures = result['enrollment_used']
    return None if figures is None else {key: m.decimal(value) for key, value in figures.items()}


def evaluate(line):
    """{plan id: result} for every plan on the line (`line` is a `shapes.LineData`)."""
    figures, results = {}, {}
    for plan in line.plans:
        enrollment, how = m.enrollment_for(plan, line)
        monthly, reason, quoted = m.monthly_premium(plan, line, enrollment) if enrollment else (None, how, False)
        figures[plan.id] = enrollment
        results[plan.id] = {
            'enrollment_used': None if enrollment is None else {k: m.plain(v) for k, v in enrollment.items()},
            'enrollment_source': how if enrollment else None,
            'monthly': m.plain(monthly),
            'annual': m.plain(monthly * 12) if monthly is not None else None,
            'reason': None if monthly is not None else reason,
            'quoted': quoted,
            'base_ids': line.base_ids(plan),
        }
    keys = m.enrollment_keys(line.rate_basis)
    for plan in line.plans:
        result = results[plan.id]
        result['change'], result['part_of'] = None, None
        bases = result['base_ids']
        if not bases or result['annual'] is None or any(results[pid]['annual'] is None for pid in bases):
            continue
        base_figures = [figures[pid] for pid in bases]
        base_people = m.total(base_figures, keys) if all(base_figures) else None
        if m.same_people(figures[plan.id], base_people):
            result['change'] = m.change(result['annual'], sum(results[pid]['annual'] for pid in bases))
        else:
            result['part_of'] = ' + '.join(line.by_id[pid].label for pid in bases)
    return results


def _words(value):
    return str(m.plain(value))


def package(plan_ids, line, results, key='', label='', missing_renewals=None):
    """One package's total, enrollment, same-people check and change against Current (§5.5)."""
    plans = [line.by_id[pid] for pid in plan_ids if pid in line.by_id]
    out = {
        'key': key,
        'label': label,
        'plan_ids': [p.id for p in plans],
        'priced': False,
        'same_people': False,
        'monthly': None,
        'annual': None,
        'enrollment': None,
        'change': None,
        'reason': None,
    }
    if not plans:
        out['reason'] = 'No plans in this package'
        return out
    unpriced = [p for p in plans if results[p.id]['monthly'] is None]
    if unpriced:
        first = unpriced[0]
        words = m.REASON_WORDS.get(results[first.id]['reason'], 'no price')
        out['reason'] = f'{first.label} has no price: {words}'
    else:
        out['priced'] = True
        out['monthly'] = sum(results[p.id]['monthly'] for p in plans)
        out['annual'] = out['monthly'] * 12
    keys = m.enrollment_keys(line.rate_basis)
    people = [_people(results[p.id]) for p in plans]
    enrollment = m.total(people, keys) if all(people) else None
    out['enrollment'] = None if enrollment is None else {k: m.plain(v) for k, v in enrollment.items()}
    if not line.current:
        return out
    current = [_people(results[p.id]) for p in line.current]
    today = m.total(current, keys) if all(current) else None
    if missing_renewals:
        out['reason'] = out['reason'] or f'No renewal entered for {missing_renewals[0]}'
        return out
    if today is None or enrollment is None:
        out['reason'] = out['reason'] or "Today's enrollment isn't complete"
        return out
    if m.same_people(enrollment, today):
        out['same_people'] = True
        annuals = [results[p.id]['annual'] for p in line.current]
        today_annual = sum(annuals) if all(a is not None for a in annuals) else None
        if out['priced'] and today_annual is not None and set(out['plan_ids']) != {p.id for p in line.current}:
            out['change'] = m.change(out['annual'], today_annual)
        return out
    diffs = [f'{k} {_words(enrollment[k])} vs {_words(today[k])}' for k in keys if enrollment[k] != today[k]]
    more = any(enrollment[k] > today[k] for k in keys)
    hint = 'are two options counted together?' if more else 'is a current plan missing?'
    out['reason'] = out['reason'] or f'Enrollment differs from today ({", ".join(diffs)}) — {hint}'
    return out


def line_packages(line, results, member_packages=()):
    """The packages shown for a line, in §5.5 order. `member_packages` is [(id, name, plan ids)]."""
    shown = []
    if line.current:
        shown.append(package([p.id for p in line.current], line, results, 'current', 'Current'))
    renewals = [p for p in line.plans if p.role == 'renewal']
    if renewals:
        renewed = {p.renews for p in renewals}
        missing = [p.label for p in line.current if p.id not in renewed]
        renewal = package([p.id for p in renewals], line, results, 'renewal', 'Renewal', missing)
        if line.current and not renewal['same_people']:
            # Its % is the "average increase" on proposals: no total unless it covers the same people (§5.5).
            renewal['monthly'] = renewal['annual'] = None
        shown.append(renewal)
    if line.current:
        carriers = []
        for plan in line.plans:
            if plan.role == 'alternate' and plan.carrier and plan.carrier not in carriers:
                carriers.append(plan.carrier)
        for carrier in carriers:
            ids = [p.id for p in line.plans if p.role == 'alternate' and p.carrier == carrier]
            result = package(ids, line, results, f'carrier:{carrier}', carrier)
            if result['same_people']:
                shown.append(result)
    for package_id, name, plan_ids in member_packages:
        shown.append(package(plan_ids, line, results, f'package:{package_id}', name))
    sold = [p.id for p in line.plans if p.sold]
    if sold:
        shown.append(package(sold, line, results, 'sold', 'Sold'))
    return shown


def coverage(line):
    """(covered, [names of current plans with no answer]); a current plan is answered by a recommended plan that renews
    or replaces it, or by being recommended itself ("Keep this plan", OQ37); a line with no current plans is covered by
    any recommended plan (§5.4). Reads links only, so it needs no prices."""
    recommended = [p for p in line.plans if p.recommended]
    if not line.current:
        return bool(recommended), [] if recommended else ['this line']
    kept = {p.id for p in recommended if p.role == 'current'}
    covered = {pid for p in recommended for pid in line.base_ids(p)} | kept
    missing = [p.label for p in line.current if p.id not in covered]
    return not missing, missing


def recommendation(line, results, member_packages=()):
    """Coverage of the recommendation and the packages made only of recommended plans (§5.4)."""
    ids = {p.id for p in line.plans if p.recommended}
    covered, missing = coverage(line)
    packages = [
        package(plan_ids, line, results, f'package:{package_id}', name)
        for package_id, name, plan_ids in member_packages
        if plan_ids and set(plan_ids) <= ids
    ]
    plan_ids = [p.id for p in line.plans if p.recommended]
    return {'plan_ids': plan_ids, 'covered': covered, 'missing': missing, 'packages': packages}
