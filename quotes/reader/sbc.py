"""The SBC reader (plan.md §10.4; D15, D38, D47, F143, OQ33; slice 22; the old claude_readers' phase 10e and
quote_reconcile's SBC merge at 891f1b3): a Summary of Benefits and Coverage read into the design of a medical plan.

- **Design values only**: an SBC states a plan's design, never its price. Rates, contributions, level-funded and
  stop-loss values are dropped whatever Claude returns (`sbc_prompt.DESIGN_KEYS`), and every plan it reads is medical.
- **Never a new plan** (D47): the SBC's plan goes to the plan it was attached to ("Attach SBC…", D38), else to the plan
  it names, by plan-number half, strong code, then carrier and name, over every role (the current plan, its renewal
  and the quotes take their design from their SBC) but never a priced version or a copy, which take theirs from the
  plan they were made from. A current plan and its renewal named alike both take it. An SBC that names no plan, or
  several unrelated ones, becomes an unticked design-only plan (an alternate) for the person to add or not.
- **Who wins**: the SBC beats a quote. A value a quote read put on the plan that the SBC prints differently is
  replaced and flagged (`low` names both figures), so the Advisor and the station count it to review; a value a person
  typed, imported or approved is left alone, unticked (D61); a sold plan is frozen (D59).
- **Always reviewed** (OQ33, D71): the reader is `must_review`, so even a direct person's read waits for review.
The change set has the quote reader's shape, so the same card shows it and `read_apply` lands it (no printed table:
an SBC's layout is not a quote's).
"""

from ai import codes
from documents import kinds as document_kinds

from .. import fields
from . import locating, rules
from .changes import Builder, _page_labels, sbc_documents
from .match import _codes_of
from .merge import norm
from .sbc_prompt import DESIGN_KEYS
from .schema import VERSION

KINDS = ('sbc',)
LINE = 'medical'
UNMATCHED = (
    'No plan on the deal matched this SBC: tick it to add it as a design-only plan, or attach the SBC to a plan.'
)
SEVERAL = 'This SBC names several plans ({names}): attach it to the one it describes.'
NOT_THERE = 'The plan this SBC was attached to is no longer on the table, so it matched no plan.'
PRICES = 'An SBC prints no prices: {n} rate or fee value{s} it returned {were} left out.'
DIFFERS = 'The SBC prints {new}; the plan had {old}.'
KEPT_TYPED = '{plan}: the SBC prints {label} as {new}; {old} stays ({why}). Tick it to use the SBC’s.'


def pool(plans):
    """The plans an SBC may fill: medical, live, never a priced version or a copy (the old `sbc_pool`)."""
    return [plan for plan in plans if plan.line == LINE and not plan.derived_from_id and plan.removed_at is None]


def _family(hits):
    """True when the hits are one plan and the plans renewing it (they share a design)."""
    return len({plan.renews_id or plan.id for plan in hits}) == 1


def match_sbc(found, plans, attached=None):
    """([plans], why) for one SBC plan: the attached plan, or every plan of the first tier that names one family."""
    if attached is not None:
        hit = next((plan for plan in plans if plan.id == attached), None)
        return ([hit], '') if hit else ([], NOT_THERE)
    number = codes.number_parts(found['plan_number'])
    tiers = (
        lambda plan: bool(number & codes.number_parts(plan.plan_number)),
        lambda plan: codes.overlap(found['codes'], _codes_of(plan)),
        lambda plan: norm(plan.name) == norm(found['name']) and norm(plan.carrier) == norm(found['carrier']),
    )
    for test in tiers:
        hits = [plan for plan in plans if test(plan)]
        if hits and _family(hits):
            return sorted(hits, key=lambda plan: (plan.role != 'current', plan.id)), ''
        if hits:
            return [], SEVERAL.format(names=', '.join(f'{plan.carrier} {plan.name}' for plan in hits[:4]))
    return [], UNMATCHED


class SbcBuilder(Builder):
    """The quote reader's builder, read as an SBC: design keys only, matched over the SBC pool, disagreements
    flagged, an unmatched SBC an unticked design-only plan."""

    def __init__(self, deal, plans, files, sbc_docs=(), attached=None):
        super().__init__(deal, plans, files, sbc_docs)
        self.pool, self.attached, self.prices = pool(plans), attached, 0
        self.used_attached = False
        self.conflicts = []  # (plan, value): where the SBC and the plan's value disagree

    def staged(self, found, plan=None):
        staged = []
        for key, entry in found['values'].items():
            if key not in DESIGN_KEYS:
                self.prices += 1 if fields.BY_KEY.get(key, {}).get('group') in ('rates', 'contrib', 'lf') else 0
                continue
            old_value = (plan.values or {}).get(key) if plan else None
            old_source = (plan.sources or {}).get(key) if plan else None
            value, problem = rules.staged_value(
                key, entry, old_value=old_value, old_source=old_source, frozen=bool(plan and plan.sold)
            )
            if problem:
                self.findings.append({'text': f'{found["carrier"]} {found["name"]}: {problem}', 'hard': False})
            if not value:
                continue
            if value['old'] not in ('', None) and not self._from_sbc(old_source):
                differs = DIFFERS.format(new=value['new'], old=value['old'])
                value['low'] = f'{value["low"]} {differs}' if value['low'] else differs
                self.conflicts.append((plan, value))
                if value['why']:
                    self.findings.append(self._kept(plan, key, value))
            staged.append(value)
        order = {key: number for number, key in enumerate(DESIGN_KEYS)}
        return sorted(staged, key=lambda value: order.get(value['key'], 999))

    def _from_sbc(self, source):
        return isinstance(source, dict) and source.get('doc') in self.sbc_docs

    def _kept(self, plan, key, value):
        label = fields.BY_KEY.get(key, {}).get('label', key)
        text = KEPT_TYPED.format(
            plan=f'{plan.carrier} {plan.name}',
            label=label,
            new=value['new'],
            old=value['old'],
            why=value['why'].lower(),
        )
        return {'text': text, 'hard': False}

    def sbc_item(self, found):
        found = {**found, 'line': LINE, 'side': 'quote'}
        attached = None if self.used_attached else self.attached
        self.used_attached = self.used_attached or attached is not None
        hits, why = match_sbc(found, self.pool, attached)
        for plan in hits:
            self.matched.add(plan.id)
            item = self.add(found, 'set_values', plan.role, plan, matched='attached' if attached else 'sbc')
            item.update(carrier=plan.carrier, name=plan.name, sbc_name=f'{found["carrier"]} {found["name"]}')
            if not item['values'] and not item['frozen']:
                item['tick'] = False
                item['why'] = 'The SBC prints nothing that differs from the plan.'
        if not hits:
            self.add(found, 'create_plan', 'alternate', tick=False, why=why, design_only=True)


def conflicts(builder):
    """[{item, plan, key, label, quote, sbc, kept}]: each value the SBC prints differently from the plan (D47), the
    review card's "Where the SBC and the quote disagree"; `kept` says why the plan's value stays, when it does."""
    out = []
    for plan, value in builder.conflicts:
        item = next((i for i in builder.items if i['plan'] == plan.id and value in (i.get('values') or [])), None)
        out.append(
            {
                'item': item['id'] if item else '',
                'plan': f'{plan.carrier} {plan.name}',
                'key': value['key'],
                'label': fields.BY_KEY.get(value['key'], {}).get('label', value['key']),
                'quote': value['old'],
                'sbc': value['new'],
                'kept': value['why'],
            }
        )
    return out


def summary(items):
    """'Design values for 1 plan · 1 design-only plan', or 'Nothing new in this SBC'."""
    filled = len({item['plan'] for item in items if item['op'] == 'set_values' and item['values']})
    new = len([item for item in items if item['op'] == 'create_plan'])
    parts = []
    if filled:
        parts.append(f'Design values for {filled} plan{"s" if filled != 1 else ""}')
    if new:
        parts.append(f'{new} design-only plan{"s" if new != 1 else ""} matched nothing')
    return ' · '.join(parts) or 'Nothing new in this SBC'


def build_changes(deal, user, merged, files, extra):
    """The change set (D.6's shape) of an SBC read: one item per plan an SBC names, in reading order."""
    from ..models import Plan

    extra = dict(extra)
    attached = extra.pop('attached', None)
    plans = list(Plan.objects.filter(deal=deal).order_by('line', 'sort_order', 'id'))
    builder = SbcBuilder(deal, plans, files, sbc_documents(deal), attached)
    for found in merged['plans']:
        builder.sbc_item(found)
    locating.locate_items(builder.items, files)
    if builder.prices:
        many = builder.prices != 1
        text = PRICES.format(n=builder.prices, s='s' if many else '', were='were' if many else 'was')
        builder.findings.append({'text': text, 'hard': False})
    values = sum(len(item.get('values') or []) for item in builder.items)
    unticked = sum(1 for item in builder.items if not item['tick']) + sum(
        1 for item in builder.items for value in item.get('values') or [] if not value['tick']
    )
    flagged = sum(1 for item in builder.items for value in item.get('values') or [] if value.get('low'))
    return {
        'v': VERSION,
        'target': 'sbc',
        'documents': [file.id for file in files],
        'attached': attached,
        'summary': summary(builder.items),
        'counts': {
            'items': len(builder.items),
            'values': values,
            'unticked': unticked,
            'flagged': flagged,
            'findings': len(builder.findings),
        },
        'items': builder.items,
        'conflicts': conflicts(builder),
        'layout': [],
        'page_labels': _page_labels(files),
        'kept': [],
        'findings': builder.findings,
        'landed': {'plan_ids': [], 'areas': []},
        **extra,
    }


def reader():
    from ai.registry import Reader

    from .. import revert_read
    from ..services import read_apply
    from . import merge, sbc_prompt, schema

    return Reader(
        target='sbc',
        kinds=KINDS,
        prompt=sbc_prompt.PROMPT,
        schema=schema.SCHEMA,
        version=schema.VERSION,
        note=sbc_prompt.note,
        merge=merge.merge,
        build_changes=build_changes,
        must_review=True,  # OQ33: an SBC read waits for review, even a direct person's (D71)
        apply=read_apply.apply,
        undo=revert_read.undo,
        labels={kind: document_kinds.label(kind) for kind in KINDS},
    )


def register():
    from ai.registry import register_reader

    register_reader(reader())
