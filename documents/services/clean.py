"""A document's details as a person sends them, cleaned (plan.md §7.4; E6, E10–E13). All-or-nothing: one bad field
refuses the whole write, so a refused kind also keeps the rename (E11)."""

from rest_framework.exceptions import ValidationError

from deals import lines

from .. import kinds
from ..checks import check_kind

DETAILS = ('kind', 'role', 'carrier', 'lines', 'label')
LIMITS = {'carrier': 200, 'label': 200}


def clean(data, current=None, require_kind=False):
    """{field: cleaned} for the fields `data` names. A kind is required on upload and may not be blanked (E6); a role
    is kept only for the kinds that ask one (E13), and a kind that does not ask clears it."""
    meta = {}
    if require_kind or 'kind' in data:
        check_kind(data.get('kind'))
        meta['kind'] = data['kind']
    kind = meta.get('kind', getattr(current, 'kind', None))
    asks = kind in kinds.ROLE_KINDS
    if 'role' in data:
        role = data['role'] or ''
        if role and role not in kinds.ROLE_KEYS:
            raise ValidationError({'role': ['Unknown document role.']})
        meta['role'] = role if asks else ''
    elif not asks and getattr(current, 'role', ''):
        meta['role'] = ''
    if 'lines' in data:
        chosen = data['lines'] or []
        if not isinstance(chosen, list) or any(line not in lines.BY_KEY for line in chosen):
            raise ValidationError({'lines': ['Lines must be line keys.']})
        meta['lines'] = [line['key'] for line in lines.LINES if line['key'] in chosen]
    for key, limit in LIMITS.items():
        if key in data:
            meta[key] = (data[key] or '').strip()[:limit]
    return meta
