"""Per-plan results for a line, packages and the recommendation (plan.md §5.4, §5.5). Pure functions.

The rule that keeps totals honest is about people: a package's change against today is shown only when it covers
the same people as today, each counted once.
"""

from . import math as m


def evaluate(line):
    """{plan id: result} for every plan on the line."""
    results = {}
    for plan in line.plans:
        enrollment, how = m.enrollment_for(plan, line)
        monthly, reason, quoted = m.monthly_premium(plan, line, enrollment) if enrollment else (None, how, False)
        results[plan.id] = {
            'enrollment_used': enrollment,
            'enrollment_source': how if enrollment else None,
            'monthly': monthly,
            'annual': monthly * 12 if monthly is not None else None,
            'reason': None if monthly is not None else reason,
            'quoted': quoted,
            'base_ids': m.base_ids(plan, line),
        }
    for plan in line.plans:
        result = results[plan.id]
        result['change'], result['part_of'] = None, None
        bases = result['base_ids']
        if not bases or result['annual'] is None:
            continue
        base_results = [results[pid] for pid in bases]
        if any(r['annual'] is None for r in base_results):
            continue
        keys = m.enrollment_keys(line.rate_basis)
        base_enrollment = (
            m._sum([r['enrollment_used'] for r in base_results], keys)
            if all(r['enrollment_used'] for r in base_results)
            else None
        )
        if m.same_enrollment(result['enrollment_used'], base_enrollment):
            result['change'] = m.change(result['annual'], sum(r['annual'] for r in base_results))
        else:
            result['part_of'] = ' + '.join(line.by_id[pid].label for pid in bases)
    return results


def _words(enrollment):
    return ', '.join(f'{k} {v:g}' for k, v in enrollment.items())


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
    if all(results[p.id]['enrollment_used'] for p in plans):
        out['enrollment'] = m._sum([results[p.id]['enrollment_used'] for p in plans], keys)
    if not line.current:
        return out
    current = [results[p.id] for p in line.current]
    today = (
        m._sum([r['enrollment_used'] for r in current], keys) if all(r['enrollment_used'] for r in current) else None
    )
    if missing_renewals:
        out['reason'] = out['reason'] or f'No renewal entered for {missing_renewals[0]}'
        return out
    if today is None or out['enrollment'] is None:
        out['reason'] = out['reason'] or "Today's enrollment isn't complete"
        return out
    if m.same_enrollment(out['enrollment'], today):
        out['same_people'] = True
        today_annual = sum(r['annual'] for r in current) if all(r['annual'] is not None for r in current) else None
        if out['priced'] and today_annual is not None and set(out['plan_ids']) != {p.id for p in line.current}:
            out['change'] = m.change(out['annual'], today_annual)
        return out
    diffs = [f'{k} {out["enrollment"][k]:g} vs {today[k]:g}' for k in keys if out['enrollment'][k] != today[k]]
    hint = (
        'are two options counted together?'
        if any(out['enrollment'][k] > today[k] for k in keys)
        else 'is a current plan missing?'
    )
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


def recommendation(line, results, member_packages=()):
    """Coverage of the recommendation and the packages made only of recommended plans (§5.4)."""
    recommended = [p for p in line.plans if p.recommended]
    ids = {p.id for p in recommended}
    if line.current:
        covered_ids = {pid for p in recommended for pid in results[p.id]['base_ids']}
        missing = [p.label for p in line.current if p.id not in covered_ids]
    else:
        missing = [] if recommended else ['this line']
    packages = [
        package(plan_ids, line, results, f'package:{package_id}', name)
        for package_id, name, plan_ids in member_packages
        if plan_ids and set(plan_ids) <= ids
    ]
    return {'plan_ids': [p.id for p in recommended], 'covered': not missing, 'missing': missing, 'packages': packages}
