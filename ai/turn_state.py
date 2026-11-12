"""What one chat turn has done so far, as its tools see it (plan.md §10.6; D80, D85, D86; slice 24).

Tools never write (D81): each adds items to the turn's change set (`add`) or sets the board (`board`). The change set
is D.6's shape with each item's `owner` (the app that lands it: quotes, intake) and `label` (what it does, in words):
  quotes: set_values {plan, line, values: [{key, label, old, new, dictated}]} · remove_plan {plan, line} ·
          clear_line {line, plans}
  intake: guidance {old, new}
Items are ticked; a person may untick some before applying a change set that waits. When the turn ends the change set
lands by itself or waits (`services/turns.py`); the board patch goes to the browser, which applies it (F108).
"""

from collections import Counter


class TurnState:
    def __init__(self, job, page, lands):
        self.job, self.deal, self.user = job, job.deal, job.created_by
        self.page = page or {}
        self.lands = lands  # the changes land when the turn ends (a direct person, the table unlocked, not lost)
        self.items, self.findings = [], []
        self.board = None  # {line, clear, config, pick?}: what set_board asked the board to show

    def add(self, item):
        """The item, numbered, ticked: `owner`, `op` and `label` are the tool's."""
        item = {'id': f't{len(self.items) + 1}', 'tick': True, 'why': '', **item}
        self.items.append(item)
        return item

    def staged(self, owner, op):
        return [item for item in self.items if item['owner'] == owner and item['op'] == op]

    def finding(self, text, hard=False):
        entry = {'text': text, 'hard': bool(hard)}
        if entry not in self.findings:
            self.findings.append(entry)

    def summary(self):
        """What the change set does, in words ("Remove 1 plan · Set 3 values")."""
        counts = Counter()
        for item in self.items:
            if item['op'] == 'set_values':
                counts['values'] += len(item.get('values') or [])
            elif item['op'] == 'remove_plan':
                counts['remove'] += 1
            else:
                counts[item['op']] += 1
        parts = []
        if counts['remove']:
            parts.append(f'Remove {counts["remove"]} plan{"s" if counts["remove"] != 1 else ""}')
        if counts['clear_line']:
            parts.append(f'Clear {counts["clear_line"]} line{"s" if counts["clear_line"] != 1 else ""}')
        if counts['values']:
            parts.append(f'Set {counts["values"]} value{"s" if counts["values"] != 1 else ""}')
        if counts['guidance']:
            parts.append('Update the client guidance')
        return ' · '.join(parts)

    def result(self, **extra):
        return {
            'v': 1,
            'target': 'turn',
            'summary': self.summary(),
            'items': self.items,
            'findings': self.findings,
            'board': self.board,
            'counts': {'items': len(self.items), 'findings': len(self.findings)},
            'landed': {'plan_ids': [], 'areas': []},
            **extra,
        }
