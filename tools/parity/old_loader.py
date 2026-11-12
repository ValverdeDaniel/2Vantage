"""Load the golden deals into old Vantage (891f1b3) from 2Vantage's own specs (plan.md §12.7, Q.5).

Runs INSIDE the old app's backend container, through its manage.py shell (tools/parity/parity.sh load):

    python manage.py shell -c "exec(open('/parity/old_loader.py').read())"

It reads the same golden/specs/gdN.json that 2Vantage's seed_golden reads (mounted read-only at PARITY_SPECS) and
applies each spec's parity profile (golden/specs.py documents both). PARITY_DEALS ("GD1,GD2") limits the deals.
Idempotent: a deal is rebuilt by its exact account name. Synthetic data and one synthetic user only.

The rows are written the way the old app writes them, through its own writers where it has one:
- the deal as the old New deal view makes it (CaseField and intake rows included), not on the client book;
- a plan as "Add plan" makes it, a PlanValue row for every plan field, made current through `current_plans`;
- a renewal through `renewal_pairs.add_renewal`, a copy through `plan_copy.duplicate_plan`;
- each value as a hand edit does (edited_value over an empty read value);
- links, typed enrollment and stars through `plan_links`, `enrollment` and `stars`;
- one recommendation per current plan, the reasons and the line counts, through `composition.merge_config`;
- the intake answers (slice 39, GD6) as the old form's hand edit stores them (CaseField.edited_value), each cleaned by
  the old app's own `intake_writes.clean_value`, so the old form shows what 2Vantage's one cleaner stores;
- a census roster (slice 41, GD4) as the old import writes a spreadsheet's people (`old_census.py`, beside this file);
- a whole line's typed counts (slice 13, GD3's `line_figures`) as the old line counts (`tier_counts_by_line`).
Then every row is read back and checked against the spec; a difference stops the load.
"""

import json
import os
import sys
from pathlib import Path

from benefits.demo_data import seed_case_fields
from benefits.market.intake import ensure_intake_fields
from benefits.market.intake_writes import clean_value
from benefits.models import BenefitFieldDef, BenefitsCase, Plan, PlanValue
from benefits.pipeline import composition, current_plans, enrollment, plan_links, stars
from benefits.pipeline.plan_copy import duplicate_plan
from benefits.pipeline.renewal_pairs import add_renewal
from django.contrib.auth import get_user_model
from django.db import transaction

SPEC_DIR = Path(os.environ.get('PARITY_SPECS', '/parity/specs'))
TOOLS_DIR = Path(os.environ.get('PARITY_TOOLS', '/parity'))  # old_census.py and golden/census_roster.py
USERNAME = os.environ.get('PARITY_USER', 'parity-admin')
PASSWORD = os.environ.get('PARITY_PASSWORD', 'parity-only-pw')


class ParityError(Exception):
    """The spec asks for something this loader or the old app cannot do."""


def parity_user():
    """The synthetic admin who owns the loaded deals; the Look lane signs in as this user."""
    user = get_user_model().objects.filter(username=USERNAME).first()
    if user is None:
        user = get_user_model().objects.create_user(USERNAME, f'{USERNAME}@example.com', PASSWORD)
    user.profile.role = 'admin'
    user.profile.save()
    return user


def specs():
    wanted = {key.strip().upper() for key in os.environ.get('PARITY_DEALS', '').split(',') if key.strip()}
    found = [json.loads(path.read_text(encoding='utf-8')) for path in sorted(SPEC_DIR.glob('gd*.json'))]
    return [spec for spec in found if not wanted or spec['key'] in wanted]


def make_case(spec, user):
    profile = spec['parity']
    if profile.get('client_book') is not None:
        raise ParityError(f"{spec['key']}: a deal on the client book needs the loader's client step (slice 6).")
    BenefitsCase.objects.filter(account_name=spec['client']).delete()
    case = BenefitsCase.objects.create(
        account_name=spec['client'],
        renewal_date=spec['effective_date'],
        requested_lines=list(spec['lines']),
        stage=profile['case'].get('stage', 'intake'),
        created_by=user,
    )
    seed_case_fields(case)
    ensure_intake_fields(case)
    case.case_fields.filter(key='legal_name', value='').update(
        value=spec['client'], confidence='high', extracted_origin='typed'
    )
    case.refresh_from_db()
    return case


def new_plan(case, plan):
    made = Plan.objects.create(
        case=case, carrier=plan['carrier'], plan_name=plan['name'], line=plan['line'], sort_order=case.plans.count() + 1
    )
    fields = BenefitFieldDef.objects.filter(domain='plan')
    PlanValue.objects.bulk_create([PlanValue(plan=made, field_def=field) for field in fields])
    return made


def typed_values(spec, plan):
    left_out = spec['parity'].get('values_left_out', {})
    return {key: str(raw).strip() for key, raw in plan['values'].items() if key not in left_out}


def hand_edit(made, values):
    """Each value as the old grid's typing writes it: the edited layer, only where it changes what shows."""
    defs = {fd.key: fd for fd in BenefitFieldDef.objects.filter(domain='plan', key__in=list(values))}
    unknown = sorted(set(values) - set(defs))
    if unknown:
        raise ParityError(f'{made}: the old app has no plan field {", ".join(unknown)}')
    for key, text in values.items():
        if not defs[key].applies_to(made.line):
            raise ParityError(f'{made}: {key} is not a {made.line} field in the old app')
        row, _ = PlanValue.objects.get_or_create(plan=made, field_def=defs[key], defaults={'extracted_value': ''})
        if row.effective_value != text:
            row.edited_value = text
            row.save(update_fields=['edited_value'])


def make_plan(spec, plan, case, user, made):
    values = typed_values(spec, plan)
    if plan['role'] == 'current':
        new = new_plan(case, plan)
        current_plans.apply(current_plans.plan_set(case, [new], 'add'))
    elif plan['role'] == 'renewal':
        new = add_renewal(case, made[plan['links'][0]])
    elif plan.get('copy_of'):
        if spec['parity'].get('copies', {}).get(plan['ref']) != 'duplicate':
            raise ParityError(f'{plan["ref"]}: the profile must say how the old app makes this copy')
        original = made[plan['copy_of']]
        shown = {pv.field_def.key: pv.effective_value for pv in original.values.select_related('field_def')}
        edits = {key: {'op': 'set', 'value': text} for key, text in values.items() if shown.get(key) != text}
        new = duplicate_plan(original, user, name=plan['name'], edits=edits)
    else:
        new = new_plan(case, plan)
    hand_edit(new, values)
    return new


def link_target(spec, plan, currents):
    """The one current plan an old option compares with, or None when the line has a single current plan."""
    if plan['role'] != 'alternate' or len(currents[plan['line']]) < 2:
        return None
    chosen = spec['parity'].get('links', {}).get(plan['ref'])
    if chosen:
        return chosen
    if len(plan['links']) != 1:
        raise ParityError(f"{plan['ref']}: links {plan['links']} need one current plan in the profile's links")
    return plan['links'][0]


def apply_marks(spec, case, made):
    plans = spec['plans']
    currents = {line: [] for line in spec['lines']}
    for plan in plans:
        if plan['role'] == 'current':
            currents[plan['line']].append(plan['ref'])
    links = {made[p['ref']].pk: made[target].pk for p in plans if (target := link_target(spec, p, currents))}
    if links:
        plan_links.apply(plan_links.plan_links(case, links))
    for line in spec['lines']:
        counts = {made[p['ref']].pk: p['enrollment'] for p in plans if p['line'] == line and p.get('enrollment')}
        if counts:
            enrollment.apply(enrollment.prepare(case, line, plans_counts=counts, on=True))
    starred = [Plan.objects.get(pk=made[ref].pk) for ref in spec['starred']]
    stars.apply(case, stars.plan_stars(case, starred, True), True)
    profile = spec['parity']
    by_current = {
        line: {str(made[current].pk): made[pick].pk for current, pick in picks.items()}
        for line, picks in profile.get('recommended_by_current', {}).items()
    }
    by_line = {line: made[ref].pk for line, ref in profile.get('recommended_by_line', {}).items()}
    typed = {p['ref']: p.get('enrollment') for p in plans}
    line_counts = {line: typed[ref] for line, ref in profile.get('line_counts', {}).items()}
    # GD3 (slice 13): a figure typed for the whole line (LineEnrollment) becomes the old line counts
    line_counts.update({line: spec['line_enrollment'][line] for line in profile.get('line_figures', [])})
    case.proposal_config = composition.merge_config(
        case.proposal_config,
        {
            'recommended_by_current': by_current,
            'recommended_plan_ids': by_line,
            'recommendation_by_line': spec['reasons'],
            'tier_counts_by_line': line_counts,
        },
    )
    case.save(update_fields=['proposal_config'])


def intake_answers(spec):
    """The spec's intake answers the old form can hold (the profile's `intake_left_out` stay out)."""
    left_out = spec['parity'].get('intake_left_out', {})
    return {key: raw for key, raw in spec.get('intake', {}).get('answers', {}).items() if key not in left_out}


def load_intake(spec, case):
    """Each answer as the old form's typing writes it: the edited layer, cleaned by the old app's own cleaner."""
    fields = {field.key: field for field in case.case_fields.all()}
    for key, raw in intake_answers(spec).items():
        field = fields.get(key)
        if field is None:
            raise ParityError(f'{spec["key"]}: the old form has no question {key}')
        text, refused = clean_value(field, ', '.join(raw) if isinstance(raw, list) else raw)
        if refused:
            raise ParityError(f'{spec["key"]}: the old cleaner refuses {key}: {refused}')
        if field.effective_value != text:
            field.edited_value = text
            field.save(update_fields=['edited_value'])


def load_census(spec, case):
    """The spec's census roster (slice 41) when the profile names its layer, read back: its differences in words."""
    layer = spec['parity'].get('census_layer')
    if layer is None:
        return []
    if layer != 'import':
        raise ParityError(f'{spec["key"]}: the loader writes a census only as the old import does, not {layer!r}')
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import old_census

    return old_census.check(case, old_census.load(spec, case))


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
    return wrong


def load(spec, user):
    with transaction.atomic():
        case = make_case(spec, user)
        load_intake(spec, case)
        census_wrong = load_census(spec, case)
        made = {}
        for plan in spec['plans']:
            made[plan['ref']] = make_plan(spec, plan, case, user, made)
        apply_marks(spec, case, made)
        wrong = check(spec, case, made) + census_wrong
        if wrong:
            raise ParityError(f'{spec["key"]} did not load as its spec says:\n  ' + '\n  '.join(wrong))
    left_out = '; '.join(item['what'] for item in spec['parity'].get('left_out', []))
    print(f'{spec["key"]} {spec["client"]}: case {case.pk}, {len(made)} plans, checked. Left out: {left_out or "-"}')
    return case


def main():
    user = parity_user()
    loaded = [load(spec, user) for spec in specs()]
    if not loaded:
        raise ParityError(f'No golden spec in {SPEC_DIR} (PARITY_DEALS={os.environ.get("PARITY_DEALS", "")!r})')


main()
