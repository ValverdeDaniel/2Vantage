"""The firm's pages and team as the client files and the builder's page ledger read them (plan.md §6.11; J42, J125,
J155; OQ41). Two light queries; no file is opened unless the caller asks for the photos (`sources`).

Nothing is filled in for the firm: blank About, figures and calendar stay blank, and a team of nobody prints no page.
The team is the deal's own pick (`config.team`, slice 34), else everyone on by default, in the firm's order.
"""

from ..models import FirmPages, TeamMember


def file_bytes(field):
    """A stored file's bytes, or None: a missing or broken file must not lose the document."""
    if not field:
        return None
    try:
        with field.open('rb') as handle:
            return handle.read()
    except Exception:  # noqa: BLE001
        return None


def firm():
    row = FirmPages.get()
    return {
        'about': (row.about_text or '').strip(),
        'stats': [s for s in (row.about_stats or []) if isinstance(s, dict)][: FirmPages.MAX_STATS],
        'calendar': [r for r in (row.service_calendar or []) if isinstance(r, dict)][: FirmPages.MAX_CALENDAR],
    }


def team(stored, sources=None):
    """[{id, name, title, group, phone, email, bio, photo}]; `photo` names the picture in `sources` (its bytes), or ''
    when there is none or the caller did not ask for pictures."""
    members = list(TeamMember.objects.all())
    picked = stored.get('team') if isinstance(stored, dict) else None
    if isinstance(picked, list):
        order = {pid: number for number, pid in enumerate(picked)}
        members = sorted((p for p in members if p.pk in order), key=lambda p: order[p.pk])
    else:
        members = [p for p in members if p.on_by_default]
    out = []
    for member in members:
        photo = file_bytes(member.photo) if sources is not None else None
        src = f'photo:{member.pk}' if photo else ''
        if photo:
            sources[src] = photo
        out.append(
            {
                'id': member.pk,
                'name': member.name,
                'title': member.title,
                'group': member.group,
                'phone': member.phone,
                'email': member.email,
                'bio': member.bio,
                'photo': src,
            }
        )
    return out


def ledger(stored):
    """What `story.ledger.rows` asks of the firm: {about, calendar, team: [{bio}]}."""
    found = firm()
    return {'about': found['about'], 'calendar': found['calendar'], 'team': team(stored)}
