"""A read's batch scope (plan.md §5.10, Q.3 #4, Q.7; I.6 "Performance"; slice 61): the per-deal reads behind each app's
`summary.facts` made once for every deal a read asks about, so the Work queue runs the same queries for 1 deal or 300.

    with batch.scope(deal_ids):
        ...  # every app's summary.facts, steps, headcounts

Inside a scope, `per_deal(name, deal_id, load)` answers from one `load(ids) -> {deal_id: value}` made for every deal
in the scope on first use, and `once(name, load)` a value no deal changes (the agency's settings). Outside a scope, or
for a deal the scope does not hold, both simply load, so every caller keeps working one deal at a time with the same
rows in the same order: a loader must answer exactly what the one-deal query answered. A scope over deals an open
scope already holds reuses it (an app's `summary.facts` opens its own scope inside agenda's).

Reads only: a scope hands out the rows it loaded, so a write inside one would read them stale; services never open
one, and a GET opens it around its read. Values are shared by every caller in the scope: a caller copies before it
changes one. Deals sits left of every app (O.1), so each app's selectors can take part without importing a right app.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import copy

_open = ContextVar('deals_batch_scopes', default=())


class Scope:
    def __init__(self, deal_ids):
        self.ids = frozenset(deal_ids)
        self.loaded = {}
        self.single = {}


def _ids(deal_ids):
    return {int(deal_id) for deal_id in deal_ids}


@contextmanager
def scope(deal_ids):
    """Batch the per-deal reads of `deal_ids` until the block ends; yields the scope."""
    wanted = _ids(deal_ids)
    holding = next((found for found in reversed(_open.get()) if wanted <= found.ids), None)
    if holding is not None:
        yield holding
        return
    found = Scope(wanted)
    token = _open.set((*_open.get(), found))
    try:
        yield found
    finally:
        _open.reset(token)


def active():
    """The innermost open scope, or None."""
    stack = _open.get()
    return stack[-1] if stack else None


def _holding(deal_id):
    return next((found for found in reversed(_open.get()) if deal_id in found.ids), None)


def holds(deal_id):
    """Whether an open scope holds the deal: a reader whose one-deal query is narrower than its batched one (a line's
    plans) takes the batched path only then, so a one-deal read outside a scope stays exactly as it was."""
    return _holding(int(getattr(deal_id, 'id', deal_id))) is not None


def per_deal(name, deal_id, load, default=None):
    """`deal_id`'s value from `load(ids) -> {deal_id: value}`: loaded once for the whole scope, or for this deal alone
    outside one. `default` answers a deal the load left out (shared: never a value a caller changes)."""
    deal_id = int(deal_id)
    found = _holding(deal_id)
    if found is None:
        return load([deal_id]).get(deal_id, default)
    if name not in found.loaded:
        found.loaded[name] = load(sorted(found.ids))
    return found.loaded[name].get(deal_id, default)


def memo(name, deal_id, compute):
    """`compute()` worked out once per deal in a scope (a value built from batched reads, asked for several times by
    one read: medical's people behind each headcount), or every time outside one. Shared: callers only read it."""
    deal_id = int(getattr(deal_id, 'id', deal_id))
    found = _holding(deal_id)
    if found is None:
        return compute()
    key = (name, deal_id)
    if key not in found.single:
        found.single[key] = compute()
    return found.single[key]


def once(name, load):
    """A value no deal changes, loaded once per scope (or every time outside one)."""
    found = active()
    if found is None:
        return load()
    if name not in found.single:
        found.single[name] = load()
    return found.single[name]


def grouped(rows, key):
    """{key(row): [rows]} keeping the rows' order: what a loader returns for one-to-many reads."""
    out = {}
    for row in rows:
        out.setdefault(key(row), []).append(row)
    return out


def _deals(ids):
    from .models import Deal

    return {deal.id: deal for deal in Deal.objects.filter(pk__in=ids).select_related('client', 'owner')}


def deal(deal_id):
    """The Deal with its client and owner, or None: one query for the whole scope. A copy, so a caller may set an
    attribute on it without another caller seeing it."""
    found = per_deal('deals.deal', deal_id, _deals)
    return copy(found) if found is not None else None


def deals(deal_ids):
    """The Deals of `deal_ids` that exist, each as `deal(id)` gives it (inside a scope, from its one query)."""
    found = (deal(deal_id) for deal_id in dict.fromkeys(int(deal_id) for deal_id in deal_ids))
    return [row for row in found if row is not None]


def client_contacts(deal_id):
    """The deal's client's contacts in their order (`sort_order`, id), a list a caller may keep."""
    from .models import Contact, Deal

    def load(ids):
        clients = dict(Deal.objects.filter(pk__in=ids).values_list('id', 'client_id'))
        by_client = grouped(
            Contact.objects.filter(client_id__in=set(clients.values())).order_by('sort_order', 'id'),
            lambda contact: contact.client_id,
        )
        return {deal_id: by_client.get(client_id, []) for deal_id, client_id in clients.items()}

    return list(per_deal('deals.contacts', deal_id, load, ()))
