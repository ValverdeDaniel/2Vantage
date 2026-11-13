"""`deal_state`: every line of a deal worked out in one grouped read (plan.md §5.4, §5.5; J.4, F.5 #37, Q.7).

A fixed number of queries whatever the plan count: the deal's live plans (removed plans never count, F60), their
`replaces` links (from the link table, never a prefetch of whole plans), the member-built packages with their live
plans, and what each line knows of its people (`people.load`: typed line figures and the census). Each line becomes a
`LineState`: its plans in `order.layout`'s order, the pure `LineData`, each plan's priced result, the packages of §5.5
and the recommendation. Medical is priced first, because worksite lines borrow its people and stop-loss counts them
(F98, OQ19). The comparison, the line counts, the proposal and (later) the client files all read it.
"""

from collections import namedtuple

from deals import batch, lines

from .. import math as m
from .. import order
from .. import packages as pk
from ..models import Package, Plan
from ..shapes import LineData, People, PlanData
from . import people as known

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
        plan_number=plan.plan_number,
        values=plan.values,
        enrollment=plan.enrollment,
        census_names=tuple(plan.census_names or ()),
        renews=plan.renews_id,
        replaces=tuple(plan.replaces_ids),
        recommended=plan.recommended,
        sold=plan.sold,
        starred=plan.starred,
        sort_order=plan.sort_order,
        version_of=version_of(plan),
        credit=(plan.derived.get('credit') or None) if version_of(plan) else None,
        pair_of=plan.pair_of_id,
    )


def line_data(line, plans, people=None):
    """`LineData` for one line's model rows, its plans in layout order; `people` (`people.load`) where it is priced."""
    people = people or People()
    data = LineData(lines.BY_KEY[line]['rate_basis'], [plan_data(p) for p in plans], key=line, people=people)
    return LineData(data.rate_basis, order.layout(data), key=line, people=people)


def _packages(ids):
    """{deal id: ([(package id, line, name)], [(package id, line, live plan id)])} for a batch scope."""
    rows = batch.grouped(Package.objects.filter(deal_id__in=ids).values_list('deal_id', 'id', 'line', 'name'), _first)
    links = Package.plans.through.objects.filter(package__deal_id__in=ids, plan__removed_at__isnull=True)
    found = batch.grouped(links.values_list('package__deal_id', 'package_id', 'package__line', 'plan_id'), _first)
    return {deal_id: (rows.get(deal_id, []), found.get(deal_id, [])) for deal_id in ids}


def _first(row):
    return row[0]


def _batched_packages(deal, line_keys):
    rows, links = batch.per_deal('quotes.packages', getattr(deal, 'id', deal), _packages, ([], []))
    wanted = set(line_keys or ())
    plan_ids = {}
    for _deal, package_id, line, plan_id in links:
        if not wanted or line in wanted:
            plan_ids.setdefault(package_id, []).append(plan_id)
    out = {}
    for _deal, package_id, line, name in rows:
        if not wanted or line in wanted:
            out.setdefault(line, []).append((package_id, name, sorted(plan_ids.get(package_id, []))))
    return out


def member_packages(deal, line_keys=None):
    """{line: [(package id, name, [live plan ids])]} in the packages' order, in two queries (two for a whole batch
    scope, `deals.batch`). A removed plan keeps its membership, hidden, so Restore brings it back into its packages
    (F60)."""
    if batch.holds(deal):
        return _batched_packages(deal, line_keys)
    packages = Package.objects.filter(deal=deal)
    if line_keys:
        packages = packages.filter(line__in=line_keys)
    rows = list(packages.values_list('id', 'line', 'name'))
    links = Package.plans.through.objects.filter(package__deal=deal, plan__removed_at__isnull=True)
    if line_keys:
        links = links.filter(package__line__in=line_keys)
    plan_ids = {}
    for package_id, plan_id in links.values_list('package_id', 'plan_id'):
        plan_ids.setdefault(package_id, []).append(plan_id)
    out = {}
    for package_id, line, name in rows:
        out.setdefault(line, []).append((package_id, name, sorted(plan_ids.get(package_id, []))))
    return out


def _plans(ids):
    """{deal id: [live plans without sources, each with `replaces_ids`]} in two queries for a batch scope."""
    links = Plan.replaces.through.objects.filter(from_plan__deal_id__in=ids, from_plan__removed_at__isnull=True)
    replaces = {}
    for from_id, to_id in links.values_list('from_plan_id', 'to_plan_id'):
        replaces.setdefault(from_id, []).append(to_id)
    plans = list(Plan.objects.filter(deal_id__in=ids).defer('sources', 'read_ref'))
    for plan in plans:
        plan.replaces_ids = sorted(replaces.get(plan.id, []))
    return batch.grouped(plans, lambda plan: plan.deal_id)


def scope_plans(deal_id):
    """The deal's live plans as the batch scope read them (without sources, with `replaces_ids`), shared by every
    reader in the scope: read them, never change one."""
    return batch.per_deal('quotes.plans', deal_id, _plans, ())


def _batched_plans(deal, line_keys):
    """`load` inside a batch scope: the scope's plans (`scope_plans`), the same instances for every reader."""
    wanted = set(line_keys or ())
    return [plan for plan in scope_plans(getattr(deal, 'id', deal)) if not wanted or plan.line in wanted]


def load(deal, line_keys=None, *, sources=False):
    """The deal's live plans (of `line_keys`, or every line), each with `replaces_ids`. `sources` only when asked:
    they are the heaviest column (F.5 #38). Inside a batch scope (`deals.batch`) the plans of every deal in it are read
    once, without their sources."""
    if not sources and batch.holds(deal):
        return _batched_plans(deal, line_keys)
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


def _line_order(key):
    return lines.LINE_KEYS.index(key) if key in lines.LINE_KEYS else 999


def _state(line, rows, people, line_members):
    rows = {plan.id: plan for plan in rows}
    data = line_data(line, list(rows.values()), people)
    results = pk.evaluate(data)
    return LineState(
        [rows[p.id] for p in data.plans],
        data,
        results,
        pk.line_packages(data, results, line_members),
        pk.recommendation(data, results, line_members),
    )


def deal_state(deal, line_keys=None, *, sources=False):
    """{line: LineState} for every line with plans (or the lines asked for, with or without plans when `line_keys`
    names them), in §4.1's line order. Every line's state is worked out once per deal in a batch scope (`deals.batch`):
    the queue's unpriced check, the proposal's lines and the headcount read the same one; callers only read it."""
    if line_keys is None and not sources and batch.holds(deal):
        return dict(batch.memo('quotes.deal_state', deal, lambda: _deal_state(deal, None)))
    return _deal_state(deal, line_keys, sources=sources)


def _deal_state(deal, line_keys=None, *, sources=False):
    plans = load(deal, line_keys, sources=sources)
    members = member_packages(deal, line_keys)
    by_line = {key: [] for key in line_keys or ()}
    for plan in plans:
        by_line.setdefault(plan.line, []).append(plan)
    keys = sorted(by_line, key=_line_order)
    people = known.load(deal.id, {*keys, known.MEDICAL})
    states = {}
    if any(known.borrows(key) for key in keys):
        rows = by_line[known.MEDICAL] if known.MEDICAL in by_line else load(deal, [known.MEDICAL])
        medical = _state(known.MEDICAL, rows, people[known.MEDICAL], members.get(known.MEDICAL, []))
        if known.MEDICAL in by_line:
            states[known.MEDICAL] = medical
        found = m.people(medical.data, medical.results)
        for key in keys:
            if known.borrows(key):
                people[key].medical = found
    for line in keys:
        if line not in states:
            states[line] = _state(line, by_line[line], people[line], members.get(line, []))
    return {key: states[key] for key in keys if by_line[key] or line_keys}


def empty(line):
    data = LineData(lines.BY_KEY[line]['rate_basis'], [], key=line)
    return LineState([], data, {}, [], pk.recommendation(data, {}))


def medical_people(deal):
    """Medical's enrolled people as `(figures, source)`, or None (the headcount's first answer, §5.7). Worked out once
    per deal in a batch scope: every headcount on a read asks for it."""

    def compute():
        state = deal_state(deal).get(known.MEDICAL) if batch.holds(deal) else None  # the scope's one state
        state = state or deal_state(deal, [known.MEDICAL])[known.MEDICAL]
        return m.people(state.data, state.results)

    return batch.memo('quotes.medical_people', deal, compute)


def people_for(deal, line):
    """One line's `People` as `deal_state` sets them, medical's people included where the line borrows them: what a
    write that prices one line (a priced version's dry run) reads."""
    found = known.load(deal.id, {line})[line]
    if known.borrows(line):
        found.medical = medical_people(deal)
    return found


def line_state(deal, line, *, sources=False):
    """One line's state: (plans, data, results, packages, recommendation)."""
    return deal_state(deal, [line], sources=sources).get(line) or empty(line)
