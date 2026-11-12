"""Stored counts: the one exception to "status is worked out on read" (plan.md §3.7, O.3.7, OQ9 c, Q.3 #9).

`census.CensusFacts` and the `flags` (open warnings) on Plan, Intake and Questionnaire are stored because the Work
queue reads every open deal. Each owner rewrites its counts in the same transaction as the write that changes them,
and registers a rebuilder here from its AppConfig.ready() (O.1's seam: deals never imports a right app):

    register('plan flags', rebuild)    # rebuild(deal_ids=None, write=False) -> [(target, stored, rebuilt)]

`manage.py rebuild_facts` (backend, the composition root) and the tests call `rebuild_all`: every count rebuilt from
the rows it counts, compared with the stored one, and (with `write`) put right. An empty answer means every stored
count is right.
"""

rebuilders = {}


def register(name, rebuild):
    rebuilders[name] = rebuild


def rebuild_all(deal_ids=None, write=False):
    """{name: [(target, stored, rebuilt)]} for every registered count, in registration order."""
    return {name: rebuild(deal_ids=deal_ids, write=write) for name, rebuild in rebuilders.items()}
