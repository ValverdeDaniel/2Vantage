"""The saved board setups a person may use (plan.md §7.8 `saved-views/`; F28, OQ7; the old advisor_filters.visible_sets
and payload): their own and every shared one, never another person's private setup, which answers 404 as if it did not
exist. A setup pinned to a line is offered on that line; one with no line on every line.
"""

from django.db.models import Q

from ..models import SavedView


def editable_by(view, user):
    """Its owner or an admin, so a shared setup never becomes unmaintainable when its author is away."""
    return bool(user.is_staff or (view.owner_id is not None and view.owner_id == user.id))


def visible(user, view=None, line=None):
    """The setups `user` may use, narrowed to one board (`view`) and to those offered on `line` when given."""
    rows = SavedView.objects.filter(Q(shared=True) | Q(owner=user)).select_related('owner')
    if view:
        rows = rows.filter(view=view)
    if line:
        rows = rows.filter(Q(line=line) | Q(line=''))
    return rows


def owner_name(view):
    owner = view.owner
    return (owner.get_full_name() or owner.username) if owner else ''


def payload(view, user):
    return {
        'id': view.id,
        'name': view.name,
        'description': view.description,
        'view': view.view,
        'line': view.line,
        'shared': view.shared,
        'config': view.config or {},
        'owner_id': view.owner_id,
        'owner_name': owner_name(view),
        'is_mine': view.owner_id is not None and view.owner_id == user.id,
        'can_edit': editable_by(view, user),
        'updated_at': view.updated_at.isoformat() if view.updated_at else None,
    }
