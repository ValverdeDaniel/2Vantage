"""`deal_state`: every line of a deal worked out in one grouped read (plan.md §5.4, §5.5; J.4, F.5 #37, Q.7).

A fixed number of queries whatever the plan count: the deal's live plans, their `replaces` links (from the link table,
never a prefetch of whole plans), and the member-built packages with their plans. Each line becomes a `LineState`:
its plans in `order.layout`'s order, the pure `LineData`, each plan's priced result, the packages of §5.5 and the
recommendation. The comparison, the line counts, the proposal and (later) the client files all read it.
"""

from collections import namedtuple

from deals import lines

from .. import order
from .. import packages as pk
from ..models import Package, Plan
from ..shapes import LineData, PlanData

LineState = namedtuple('LineState', 'plans data results packages recommendation')


def replaced_ids(**where):
    """{plan id: [ids of the current plans it replaces]} from the link table, e.g. `from_plan__deal=deal` or
    `from_plan_id__in=ids`: one light query, never whole plans."""
    rows = Plan.replaces.through.objects.filter(**where).values_list('from_plan_id', 'to_plan_id')
    out = {}
    for from_id, to_id in rows:
        out.setdefault(from_id, []).append(to_id)
    return out


def version_of(plan):
    """The plan a priced version rides behind; a duplicate is a standalone peer (D-049)."""
    return plan.derived_from_id if plan.derived_from_id and plan.derived.get('kind') != 'duplicate' else None


def plan_data(plan):
    """A model row (with `replaces_ids` set) as the pure rules read it."""
    return PlanData(
        id=plan.id,
        role=plan.role,
        carrier=plan.carrier,
        name=plan.name,
        values=plan.values,
        enrollment=plan.enrollment,
        enrollment_on=plan.enrollment_on,
        renews=plan.renews_id,
        replaces=tuple(plan.replaces_ids),
        recommended=plan.recommended,
        sold=plan.sold,
        starred=plan.starred,
        sort_order=plan.sort_order,
        version_of=version_of(plan),
    )


def line_data(line, plans):
    """`LineData` for one line's model rows, its plans in layout order."""
    data = LineData(lines.BY_KEY[line]['rate_basis'], [plan_data(p) for p in plans], key=line)
    return LineData(data.rate_basis, order.layout(data), key=line)


def member_packages(deal, line_keys=None):
    """{line: [(package id, name, [plan ids])]} in the packages' order, in two queries."""
    packages = Package.objects.filter(deal=deal)
    if line_keys:
        packages = packages.filter(line__in=line_keys)
    rows = list(packages.values_list('id', 'line', 'name'))
    links = Package.plans.through.objects.filter(package__deal=deal)
    if line_keys:
        links = links.filter(package__line__in=line_keys)
    plan_ids = {}
    for package_id, plan_id in links.values_list('package_id', 'plan_id'):
        plan_ids.setdefault(package_id, []).append(plan_id)
    out = {}
    for package_id, line, name in rows:
        out.setdefault(line, []).append((package_id, name, sorted(plan_ids.get(package_id, []))))
    return out


def load(deal, line_keys=None, *, sources=False):
    """The deal's live plans (of `line_keys`, or every line), each with `replaces_ids`. `sources` only when asked:
    they are the heaviest column (F.5 #38)."""
    plans = Plan.objects.filter(deal=deal)
    if line_keys:
        plans = plans.filter(line__in=line_keys)
    if not sources:
        plans = plans.defer('sources', 'read_ref')
    plans = list(plans)
    where = {'from_plan__deal': deal, 'from_plan__removed_at__isnull': True}
    if line_keys:
        where['from_plan__line__in'] = line_keys
    links = replaced_ids(**where)
    for plan in plans:
        plan.replaces_ids = sorted(links.get(plan.id, []))
    return plans


def deal_state(deal, line_keys=None, *, sources=False):
    """{line: LineState} for every line with plans (or the lines asked for), in §4.1's line order."""
    plans = load(deal, line_keys, sources=sources)
    members = member_packages(deal, line_keys)
    by_line = {}
    for plan in plans:
        by_line.setdefault(plan.line, []).append(plan)
    states = {}
    for line in sorted(by_line, key=lambda key: lines.LINE_KEYS.index(key) if key in lines.LINE_KEYS else 999):
        rows = {plan.id: plan for plan in by_line[line]}
        data = line_data(line, list(rows.values()))
        results = pk.evaluate(data)
        line_members = members.get(line, [])
        states[line] = LineState(
            [rows[p.id] for p in data.plans],
            data,
            results,
            pk.line_packages(data, results, line_members),
            pk.recommendation(data, results, line_members),
        )
    return states


def empty(line):
    data = LineData(lines.BY_KEY[line]['rate_basis'], [], key=line)
    return LineState([], data, {}, [], pk.recommendation(data, {}))


def line_state(deal, line, *, sources=False):
    """One line's state: (plans, data, results, packages, recommendation)."""
    return deal_state(deal, [line], sources=sources).get(line) or empty(line)
