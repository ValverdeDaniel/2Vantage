"""Revert of a proposal Activity row (plan.md §3.7, O.3.2; J.6.10): a setting's earlier value, a card's mark.
Registered as `activity.reverters['proposal']` in ProposalsConfig.ready().

`deals.activity.revert` has already locked the Deal; this locks the config row. It refuses after a later write to the
same path (naming it), and otherwise puts each path's "before" back — a setting into `config`, a mark into `marks`
(paths "marks.…"). Returns the changes it wrote.
"""

from deals import activity, lines

from . import catalog, config
from .models import ProposalConfig

WORDS = {
    'title': 'The title',
    'intro': 'The introduction',
    'recommendation': 'The recommendation words',
    'order': 'The line order',
    'next_steps': 'The next steps',
    'output.layout': 'The layout',
    'output.package_summary': 'The package summary switch',
    'output.compare_tabs': "The spreadsheet's “Every quoted plan” switch",
    'output.disclaimers': "The spreadsheet's Disclaimers switch",
    'output.compare_slots': 'The Compare columns',
    'experience.summary': 'The plan experience summary',
    'experience.rows': 'The plan experience periods',
    'summary.on': "The executive summary's Show it",
    'summary.blocks': "The executive summary's figures",
    'markets.on': "Markets checked's Show it",
}
PAGE_LABELS = dict(catalog.PAGES)


def label(path):
    """A path in words, for the refusal ("The reasons for Medical were changed after this…")."""
    parts = path.split('.')
    if path in WORDS:
        return WORDS[path]
    if parts[0] == 'reasons':
        return f'The reasons for {lines.label(parts[1])}'
    if parts[0] == 'marks':
        card = parts[-1]
        return f'The completed mark on {catalog.CARD_TITLES.get(card, card)}'
    if parts[0] == 'lines':
        return f'{lines.label(parts[1])}: {parts[2].replace("_", " ")}'
    if parts[:2] == ['output', 'pages']:
        return f'The switch for the {PAGE_LABELS.get(parts[2], parts[2])} page'
    if parts[:2] == ['markets', 'lines']:
        what = 'the hidden carriers' if parts[3] == 'hidden' else "a carrier's note"
        return f'Markets checked on {lines.label(parts[2])}: {what}'
    return path


def revert(row, user):  # noqa: ARG001 (the reverters' signature)
    later = activity.later_keys(row)
    if later:
        keys = sorted(later)
        raise activity.changed_since([label(key) for _target, key in keys], [key for _target, key in keys])
    stored = ProposalConfig.objects.select_for_update().get(deal_id=row.deal_id)
    written = []
    for entry in row.changes:
        diff = {}
        for path, (before, _after) in entry['k'].items():
            mark = path.startswith('marks.')
            bucket = stored.marks if mark else stored.config
            key = path.removeprefix('marks.') if mark else path
            now = (config.get(bucket, key) or None) if mark else config.get(bucket, path)
            if mark and before:
                config.place(bucket, key, before)
            elif mark:
                config.drop(bucket, key)
            else:
                config.put(bucket, key, before)
            diff[path] = [now, before]
        written.append(activity.change(entry['t'], diff))
    stored.save(update_fields=['config', 'marks', 'updated_at'])
    return written
