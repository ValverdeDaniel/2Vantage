"""Applying a read plan template (plan.md §9.3): every change, or nothing.

`template.read` parses and checks the file and writes nothing; here each operation goes through the plan doors: a new
plan through `create_plan`, details and values through `update_plan` (origin `import`, the cell in each source), and
a changed role or links through `roles`. A value or detail the file repeats changes nothing.
"""

from django.db import transaction

from . import roles
from .plans import create_plan, update_plan

DETAILS = ('carrier', 'name', 'plan_number')


def _details(op):
    """The existing plan's carrier, name and number that the file changes; what it repeats is left out."""
    plan, head = op['plan'], op['head']
    return {key: head[key] for key in DETAILS if head[key] and head[key] != getattr(plan, key)}


def _links_change(op):
    """(role, renews id, replaced ids) when the file changes the plan's role or links, else None."""
    plan, head, role, ids = op['plan'], op['head'], op['role'], op['links']
    renews = ids[0] if role == 'renewal' and ids else None
    if role == plan.role and not head['link']:
        return None
    current = plan.renews_id if plan.role == 'renewal' else None
    replaced = sorted(p.id for p in plan.replaces.all()) if plan.role == 'alternate' else []
    if role == plan.role and renews == current and sorted(ids if role == 'alternate' else []) == replaced:
        return None
    return role, renews, ids if role == 'alternate' else []


def would_change(op):
    """Whether the file changes an existing plan's details, role or links (the dry run's count)."""
    return bool(_details(op)) or _links_change(op) is not None


@transaction.atomic
def apply_template(user, deal, operations, document):
    created = updated = cells = 0
    for op in operations:
        head, plan = op['head'], op['plan']
        if plan is None:
            create_plan(
                user,
                deal,
                line=op['line'],
                role=op['role'],
                carrier=head['carrier'],
                name=head['name'],
                plan_number=head['plan_number'],
                renews_id=op['links'][0] if op['role'] == 'renewal' and op['links'] else None,
                replaces_ids=op['links'] if op['role'] == 'alternate' else [],
                values=op['values'],
                source_origin='import',
                document=document,
                cells=op['cells'],
            )
            created += 1
            cells += len(op['values'])
            continue
        details, links = _details(op), _links_change(op)
        if links is not None:
            role, renews, replaces = links
            if role != plan.role:
                roles.set_role(user, deal, [plan.id], role, renews, replaces)
            else:
                roles.set_links(user, deal, plan.id, replaces if role == 'alternate' else None, renews)
        _, changed = update_plan(user, plan.id, {'values': op['values'], **details}, 'import', document, op['cells'])
        if changed or details or links is not None:
            updated += 1
        cells += len(changed)
    return {'create': created, 'update': updated, 'cells_changed': cells}
