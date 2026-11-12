"""GD3's checkpoints after its seed (plan.md §13.4, Q.4; slice 13), each through the services a person's clicks call.

The seed builds checkpoint A as it starts: no current plan, ten quotes priced from the medical line's typed figure.
Then, in order:
- `arrive(user, built, ref)`: one of the renewal packet's current plans (`arrivals`) lands, with its values; from
  slice 18 the packet's read brings them. The second one stops the line figure (per_plan_counts_needed, F88).
- `split(user, built)`: the packet's printed per-plan counts typed into the counts card, and each quote told what it
  replaces (`links_after_split`; OQ20).
- `census(user, built)`: checkpoint B, a census of 48 enrolled employees naming both current plans, imported (F91).
Each returns the Golden with `refs` grown by the plans it made. Tests reach these through the root conftest only.
"""

from quotes import services as plans

from . import census_files
from .seed import Golden


def arrive(user, built, ref):
    deal, refs, spec = built
    plan = next(p for p in spec['arrivals'] if p['ref'] == ref)
    made = plans.create_plan(
        user, deal, line=plan['line'], role='current', carrier=plan['carrier'], name=plan['name'], values=plan['values']
    )
    return Golden(deal, {**refs, ref: made.id}, spec)


def split(user, built):
    deal, refs, spec = built
    typed = [{'id': refs[p['ref']], 'enrollment': p['enrollment']} for p in spec['arrivals'] if p.get('enrollment')]
    plans.set_enrollment(user, deal, 'medical', plans=typed)
    for ref, replaced in spec['links_after_split'].items():
        plans.set_links(user, deal, refs[ref], replaces_ids=[refs[current] for current in replaced])
    return built


def census(user, built):
    deal, _refs, spec = built
    census_files.arrive(user, deal, spec)
    return built
