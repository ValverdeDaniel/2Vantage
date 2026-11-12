"""Landing a read's plans and values (plan.md §10.5; D59–D62, D72, D115, D117, F120, F138, F141): the plan items of a
change set a person chose to use, written by `read_apply` inside its transaction, on the lines' plans it locked.

- **A new plan** gets the read's carrier, name, plan number and codes, the read's reference (`read_ref`: its match key,
  file and job, so the next read finds it, D59), its file, and the next number on its line, so new plans arrive in the
  quote's reading order (D62, F138). A renewal renews the current plan the read named (made by this read, picked, or
  already on the deal) and leads its plan's group (F120); one whose current plan is not there is an alternate, and one
  whose current plan already has a renewal is an alternate replacing it. A quote replaces the current plans the file
  named, when the reader was sure or the person ticked it (D115).
- **Values** land with `origin: ai`, their file, page or cell, printed line, the locator's answer and any doubt, and
  the read value (O.3.1, F141). On a plan the deal had, a value lands only while it is still what the person saw in the
  review; one changed since is left as it is and said (D31's "stale"). A sold plan is frozen (D59).
- **Never twice** (D117): a plan the deal gained since the read, or a current plan on a line that has one now, is not
  made again; it is said, and its counts and renewal go to the plan already there.
"""

from deals import activity
from deals.values import apply as apply_values
from deals.values import source

from .. import fields
from ..models import Plan
from ..reader import rules
from ..reader.choice import ALTERNATE, NEW
from ..reader.match import match
from .plans import next_number, placed

SIDE_OF_ROLE = {'current': 'current', 'renewal': 'renewal', 'alternate': 'quote'}
READ_REF = 'plan.read_ref'  # the key that marks a plan the read made (Undo removes it, D73)
ORDER = 'plan.sort_order'

GONE = 'its plan is no longer on this line, so nothing was written to it.'
ON_DEAL = 'already on the deal (added since this read), so it was not added again.'
NOW_CURRENT = 'this line has a current plan now, so it was not added as another. Read the file again to match it.'
STALE = '{label} changed since this read, so it was left as it is.'
HAS_RENEWAL = '{current} already has a renewal, so this was added as a quote replacing it.'
LEFT = '{label} was left alone ({why}).'


def label_of(plan):
    return f'{plan.carrier} {plan.name}'


def _found(item, role):
    """The item as the matcher sees a plan the read found (match.py)."""
    return {
        'line': item['line'],
        'side': SIDE_OF_ROLE.get(role, 'quote'),
        'carrier': item['carrier'],
        'name': item['name'],
        'plan_number': item.get('plan_number') or '',
        'codes': list(item.get('codes') or []),
    }


def _source_for(user, values):
    by_key = {value['key']: value for value in values}

    def make(key):
        value = by_key[key]
        return source(
            'ai',
            user,
            doc=value.get('doc'),
            page=value.get('page'),
            cell=value.get('cell') or None,
            line=value.get('line') or None,
            loc=value.get('loc') or None,
            low=value.get('low') or None,
            read_value=value['new'],
        )

    return make


class Landing:
    def __init__(self, user, deal, rows, job):
        self.user, self.deal, self.job = user, deal, job
        self.rows = rows  # {id: plan}: the lines' live plans, locked by the caller
        self.before = list(rows.values())  # the plans as they were before this landing
        self.by_item = {}  # change-set item id -> the plan it became or went to
        self.created, self.renewals = [], []
        self.diffs = {}  # plan id -> {key: [before, after]}, in reading order
        self.sources = {}  # 'plan:<id>' -> {key: the source entry a landed value replaced}, for Undo
        self.skipped = []

    def say(self, item, text):
        self.skipped.append(f'{item["carrier"]} {item["name"]}: {text}')

    def resolve(self, target):
        """The plan an item's `renews`, `replaces` or counts point at: one this read made or placed, or the deal's."""
        if not target:
            return None
        if target.get('item'):
            return self.by_item.get(target['item'])
        plan = self.rows.get(target.get('plan'))
        return plan if plan is not None and plan.removed_at is None else None

    def land(self, chosen):
        item = chosen.item
        if item['op'] == 'create_plan':
            return self.create(chosen, item['role'])
        if item['op'] == 'pick_current' and chosen.pick in (NEW, ALTERNATE):
            return self.create(chosen, 'current' if chosen.pick == NEW else 'alternate', fresh=False)
        plan = self.rows.get(chosen.pick if item['op'] == 'pick_current' else item.get('plan'))
        if plan is None or plan.line != item['line']:
            return self.say(item, GONE)
        self.by_item[item['id']] = plan
        if not plan.sold:  # a sold plan is frozen (D59)
            self.fill(plan, chosen, picked=item['op'] == 'pick_current')
        return plan

    def fill(self, plan, chosen, picked):
        changes = {}
        for value in chosen.values:
            key = value['key']
            now = plan.values.get(key)
            name = fields.BY_KEY.get(key, {}).get('label', key)
            if picked:  # the review drew these against no plan: the rule decides against the one picked (D61)
                verdict = rules.decide(now, plan.sources.get(key), value['new'])
                if isinstance(verdict, tuple):
                    self.say(chosen.item, LEFT.format(label=name, why=verdict[1].lower()))
                if verdict in ('fill', 'replace'):
                    changes[key] = value['new']
            elif str(now or '') == str(value.get('old') or ''):
                changes[key] = value['new']
            elif str(now or '') != str(value['new']):
                self.say(chosen.item, STALE.format(label=name))
        before = {key: dict(plan.sources[key]) for key in changes if isinstance(plan.sources.get(key), dict)}
        diff = apply_values(plan.values, plan.sources, changes, _source_for(self.user, chosen.values))
        if not diff:
            return
        plan.save(update_fields=['values', 'sources', 'updated_at'])
        self.diffs.setdefault(plan.id, {}).update(diff)
        kept = {key: entry for key, entry in before.items() if key in diff}
        if kept:
            self.sources.setdefault(f'plan:{plan.id}', {}).update(kept)

    def _role(self, chosen, role):
        """(role, renews id, [replaced ids]) for a new plan, from what the read named and the line holds now."""
        item, line = chosen.item, chosen.item['line']
        if role == 'renewal':
            current = self.resolve(item.get('renews'))
            if current is None or current.role != 'current' or current.line != line:
                return 'alternate', None, []
            taken = [p for p in self.rows.values() if p.role == 'renewal' and p.renews_id == current.id]
            if taken:
                self.say(item, HAS_RENEWAL.format(current=label_of(current)))
                return 'alternate', None, [current.id]
            return 'renewal', current.id, []
        if role == 'alternate' and chosen.replaces:
            named = [self.resolve(target) for target in item['replaces']['to']]
            return 'alternate', None, sorted({p.id for p in named if p and p.role == 'current' and p.line == line})
        return role, None, []

    def create(self, chosen, role, fresh=True):
        item, line = chosen.item, chosen.item['line']
        if fresh:  # the review said "new": check nothing like it arrived since (D117)
            current = self.resolve(item.get('renews')) if role == 'renewal' else None
            hit, _how = match(_found(item, role), [p for p in self.before if p.line == line], renews_plan=current)
            if hit is not None:
                self.by_item[item['id']] = hit
                return self.say(item, ON_DEAL)
            if role == 'current' and any(p.line == line and p.role == 'current' for p in self.before):
                return self.say(item, NOW_CURRENT)
        role, renews, replaces = self._role(chosen, role)
        docs = list(item.get('docs') or [])
        ref = {'key': item.get('read_ref') or '', 'doc': docs[0] if docs else None, 'job': self.job.id}
        plan = Plan(
            deal=self.deal,
            line=line,
            role=role,
            carrier=str(item['carrier'])[:200],
            name=str(item['name'])[:200],
            plan_number=str(item.get('plan_number') or '')[:100],
            codes=list(item.get('codes') or []),
            read_ref=ref,
            renews_id=renews,
            source_document_id=docs[0] if docs else None,
            sort_order=next_number(self.deal, line),
        )
        values = {value['key']: value['new'] for value in chosen.values}
        diff = apply_values(plan.values, plan.sources, values, _source_for(self.user, chosen.values))
        plan.save()
        if replaces:
            plan.replaces.set(replaces)
        plan.replaces_ids = replaces
        self.rows[plan.id] = plan
        self.by_item[item['id']] = plan
        self.created.append(plan)
        self.diffs[plan.id] = {READ_REF: [None, ref], **diff}
        if role == 'renewal':
            self.renewals.append(plan)
        return plan

    def place(self):
        """Each new renewal leads its plan's group (F120); the plans it passes are recorded with the landing."""
        made = {plan.id for plan in self.created}
        for plan in self.renewals:
            for change in placed(self.deal, plan):
                plan_id = int(change['t'].partition(':')[2])
                if plan_id in made:
                    continue
                before, after = change['k'][ORDER]
                diff = self.diffs.setdefault(plan_id, {})
                diff[ORDER] = [diff[ORDER][0] if ORDER in diff else before, after]

    def entries(self):
        return [activity.change(f'plan:{plan_id}', diff) for plan_id, diff in self.diffs.items() if diff]

    def words(self):
        """'2 current plans · 2 renewals · values on 1 plan', '' when nothing landed."""
        nouns = {'current': ('current plan', 'current plans'), 'renewal': ('renewal', 'renewals')}
        roles = {}
        for plan in self.created:
            roles[plan.role] = roles.get(plan.role, 0) + 1
        parts = [f'{n} {nouns.get(role, ("quote", "quotes"))[n != 1]}' for role, n in roles.items()]
        made = {plan.id for plan in self.created}
        updated = [pid for pid, diff in self.diffs.items() if pid not in made and set(diff) - {ORDER}]
        if updated:
            parts.append(f'values on {len(updated)} plan{"s" if len(updated) != 1 else ""}')
        return ' · '.join(parts)
