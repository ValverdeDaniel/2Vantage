"""The golden loader's read-back (tools/parity/old_loader.py): what a spec asks of the old app, and every loaded row
checked against it, plus GD5's stop-loss answer key. Read only; it writes nothing. Mounted beside the loader at
/parity/old_checks.py and imported from there (the loader runs through the old app's manage.py shell)."""

from benefits.market.intake_writes import clean_value
from benefits.models import Plan
from benefits.pipeline import enrollment
from benefits.pipeline.plan_merge import clean_merged


def typed_values(spec, plan):
    left_out = spec['parity'].get('values_left_out', {})
    typed = {key: str(raw).strip() for key, raw in plan['values'].items() if key not in left_out}
    if plan.get('plan_number'):  # a column in 2Vantage, a plan value in the old app
        typed['plan_number'] = str(plan['plan_number']).strip()
    return typed


def intake_answers(spec):
    """The spec's intake answers the old form can hold (the profile's `intake_left_out` stay out)."""
    left_out = spec['parity'].get('intake_left_out', {})
    return {key: raw for key, raw in spec.get('intake', {}).get('answers', {}).items() if key not in left_out}


def check(spec, case, made):
    """Read every loaded row back and compare it with the spec. Returns the differences, in words."""
    names = {plan.pk: ref for ref, plan in made.items()}
    wrong = []
    for plan in spec['plans']:
        row = Plan.objects.get(pk=made[plan['ref']].pk)
        got = (row.carrier, row.plan_name, row.line, row.is_current)
        want = (plan['carrier'], plan['name'], plan['line'], plan['role'] == 'current')
        if got != want:
            wrong.append(f'{plan["ref"]}: {got} != {want}')
        if plan['role'] == 'renewal' and names.get(row.renewal_of_id) != plan['links'][0]:
            wrong.append(f'{plan["ref"]}: renews {names.get(row.renewal_of_id)}, not {plan["links"][0]}')
        shown = {pv.field_def.key: pv.effective_value for pv in row.values.select_related('field_def')}
        for key, text in typed_values(spec, plan).items():
            if shown.get(key) != text:
                wrong.append(f'{plan["ref"]}.{key}: {shown.get(key)!r} != {text!r}')
        typed = enrollment.typed_counts(row)
        if typed != plan.get('enrollment') or (typed and not row.enrollment.get('on')):
            wrong.append(f'{plan["ref"]}: enrollment {row.enrollment} != {plan.get("enrollment")}')
        if row.is_shortlisted != (plan['ref'] in spec['starred']):
            wrong.append(f'{plan["ref"]}: starred {row.is_shortlisted}')
    fields = {field.key: field for field in case.case_fields.all()}
    for key, raw in intake_answers(spec).items():
        text, _ = clean_value(fields[key], ', '.join(raw) if isinstance(raw, list) else raw)
        if fields[key].effective_value != text:
            wrong.append(f'intake.{key}: {fields[key].effective_value!r} != {text!r}')
    case.refresh_from_db()
    stored = case.proposal_config.get('tier_counts_by_line') or {}
    typed = {plan['ref']: plan.get('enrollment') for plan in spec['plans']}
    for line, ref in spec['parity'].get('line_counts', {}).items():
        if stored.get(line) != typed[ref]:
            wrong.append(f'{line}: line counts {stored.get(line)} != {ref} {typed[ref]}')
    for line in spec['parity'].get('line_figures', []):
        if stored.get(line) != spec['line_enrollment'][line]:
            wrong.append(f'{line}: line figure {stored.get(line)} != {spec["line_enrollment"][line]}')
    merged = (case.proposal_config.get('composition') or {}).get('lines') or {}
    for first, second in spec.get('pairs', []):
        line = next(plan['line'] for plan in spec['plans'] if plan['ref'] == first)
        if [made[first].pk, made[second].pk] not in clean_merged((merged.get(line) or {}).get('merged')):
            wrong.append(f'{first} + {second}: not printed as one column on {line}')
    return wrong


def stop_loss_figures(spec, case):
    """GD5 (slice 36): the old app's own stop-loss verdict for each plan of the Stop-Loss line, printed after the load,
    so the old app serves as an answer key for golden/keys/gd5.json (plan.md §12.6): the headcount every PEPM
    multiplies (`stop_loss_enrolled`, the medical tally) and each plan's annual premium, attachment, laser liability
    and maximum annual liability, from `stop_loss_math.stop_loss_summary`. Nothing is written."""
    if 'stop_loss' not in spec['lines']:
        return
    from benefits.pipeline.plan_math import stop_loss_enrolled
    from benefits.pipeline.stop_loss_math import stop_loss_summary

    headcount = stop_loss_enrolled(case)
    print(f'{spec["key"]} stop-loss: {headcount} enrolled employees x 12 months')
    plans = [p for p in spec['plans'] if p['line'] == 'stop_loss']
    names = {(p['carrier'], p['name'], p['role'] == 'current'): p['ref'] for p in plans}
    for row in case.plans.filter(line='stop_loss'):
        values = {pv.field_def.key: pv.effective_value for pv in row.values.select_related('field_def')}
        found = stop_loss_summary(values, headcount)
        ref = names.get((row.carrier, row.plan_name, row.is_current), row.pk)
        figures = ', '.join(f'{key} {found[key]}' for key in (
            'annual_premium', 'annual_attachment', 'laser_liability', 'max_annual_liability'))
        print(f'  {ref}: {figures}')
