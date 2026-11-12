"""Saved parts of a proposal, read side (plan.md §6.11, §7.12 `proposal/templates/`; J68, OQ7; old Vantage 891f1b3
`pipeline/proposal_templates.py` and `TemplateBar.jsx`): what each kind holds, the built-in layout, who may use and
change a template, and its payload.

A template's `config` is {path: value}, each value cleaned by `config.clean`, so a template and a deal can never hold
two shapes for one setting:
- `layout`: every `output` path (`config.output_paths()`), the look of the PDF, the PowerPoint and the spreadsheet;
- `rows`: `rows` and `card_stats`, relative to the line it is applied on (a key the line lacks is dropped there);
- `summary`: `summary.on` and `summary.blocks`.
A bad value falls back to the default (a renamed key must not brick a stored template); a path the kind does not hold
is dropped. "Vantage default" ships in code (Q6): every layout path at its default, so a deal nobody touched matches
it and applying it undoes every look choice. It is offered under "Built in" and never changed or deleted.
"""

from django.db.models import Q

from . import config
from .cleaners import Invalid
from .models import ProposalTemplate

BUILT_IN_ID = 'vantage-default'
ROW_KEYS = ('rows', 'card_stats')
SUMMARY_PATHS = ('summary.on', 'summary.blocks')


def paths(kind):
    if kind == ProposalTemplate.LAYOUT:
        return config.output_paths()
    if kind == ProposalTemplate.SUMMARY:
        return list(SUMMARY_PATHS)
    return list(ROW_KEYS)


def _cleaned(path, raw):
    try:
        return config.clean(path, raw)[1]
    except Invalid:
        return config.default(path)


def _keys(raw, limit):
    if not isinstance(raw, list):
        return None
    out = []
    for item in raw:
        key = str(item or '').strip()[:60]
        if key and key not in out:
            out.append(key)
    return out[:limit]


def clean_config(kind, raw, line=''):
    """{path: value} for `kind`, every path the kind holds present. A `rows` template on one line is cleaned against
    that line's fields; one for any line keeps the keys as given, each line dropping those it lacks when applied."""
    raw = raw if isinstance(raw, dict) else {}
    if kind != ProposalTemplate.ROWS:
        return {path: _cleaned(path, raw[path]) if path in raw else config.default(path) for path in paths(kind)}
    if line:
        return {key: _cleaned(f'lines.{line}.{key}', raw.get(key)) for key in ROW_KEYS}
    return {'rows': _keys(raw.get('rows'), 80), 'card_stats': _keys(raw.get('card_stats'), 6) or None}


def built_in(kind):
    """The templates that ship with the app, shaped as `payload` shapes a saved one."""
    if kind != ProposalTemplate.LAYOUT:
        return []
    return [
        {
            'id': BUILT_IN_ID,
            'name': 'Vantage default',
            'description': 'The 16:9 Presentation format, every page on, with a picture on the cover and the '
            'thank-you page.',
            'kind': ProposalTemplate.LAYOUT,
            'line': '',
            'config': {path: config.default(path) for path in paths(ProposalTemplate.LAYOUT)},
            'shared': True,
            'owner_id': None,
            'owner_name': '',
            'is_mine': False,
            'can_edit': False,
            'built_in': True,
            'updated_at': None,
        }
    ]


def editable_by(template, user):
    """Its owner or an admin, so a shared template never becomes unmaintainable when its author is away."""
    return bool(user.is_staff or (template.owner_id is not None and template.owner_id == user.id))


def visible(user, kind=None, line=None):
    """The templates `user` may use: their own and every shared one, narrowed to a kind and to those offered on
    `line` (a template with no line is offered on every line)."""
    rows = ProposalTemplate.objects.filter(Q(shared=True) | Q(owner=user)).select_related('owner')
    if kind:
        rows = rows.filter(kind=kind)
    if line:
        rows = rows.filter(Q(line=line) | Q(line=''))
    return rows


def payload(template, user):
    owner = template.owner
    return {
        'id': template.id,
        'name': template.name,
        'description': template.description,
        'kind': template.kind,
        'line': template.line,
        'config': template.config or {},
        'shared': template.shared,
        'owner_id': template.owner_id,
        'owner_name': (owner.get_full_name() or owner.username) if owner else '',
        'is_mine': template.owner_id is not None and template.owner_id == user.id,
        'can_edit': editable_by(template, user),
        'built_in': False,
        'updated_at': template.updated_at.isoformat() if template.updated_at else None,
    }
