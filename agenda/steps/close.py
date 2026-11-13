"""The close track and the step after the sale (I56–I60, I63; plan.md §5.9, OQ91). Pure.

- `build_proposal`: built when our recommendation covers every line that needs one (proposals' Issue gate, §5.4) or
  a proposal was issued; "Build the proposal — m of n lines recommended" until then (I56).
- `issue_proposal`: "Issue the proposal to the client", then "Proposal issued (vN)" (I57).
- `follow_up_selection`: from the latest issue, waiting under 7 days, then a follow-up (I58).
- `mark_sold`: blocked until the proposal is issued, then open, then "Sold" (I60).
- After the sale the commission step leads: "Enter the commission for N sold lines", then it is done and the deal
  reads "Sold" (I63; OQ91 as changed by OQ101 c).
Words from old Vantage 891f1b3 `tasks/steps.py` `_proposal_steps`, with the issue in place of the share link.
"""

from datetime import timedelta

from .. import rules
from .base import Steps, days_since, local_day

AFTER_QUOTES = 'After the carrier quotes are in'
AFTER_BUILT = 'After the proposal is built'
AFTER_ISSUED = 'After the proposal is issued'


def add(s: Steps, facts, sit):
    if sit.sold:
        s.add('mark_sold', 'Sold', state='done')
        _commission(s, facts)
        return
    if not sit.quotes_in:
        s.add('build_proposal', 'Build the proposal', state='blocked', blocked_by='read_quotes', reason=AFTER_QUOTES)
        s.add('issue_proposal', 'Issue the proposal to the client', state='blocked', blocked_by='build_proposal',
              reason=AFTER_BUILT)  # fmt: skip
        s.add('mark_sold', 'Mark the winning plan sold', state='blocked', blocked_by='read_quotes', reason=AFTER_QUOTES)
        return
    proposals = facts.get('proposals') or {}
    latest = proposals.get('latest')
    built = bool(latest) or bool(proposals.get('ready'))
    if built:
        s.add('build_proposal', 'Proposal built', state='done')
    else:
        needs, picked = proposals.get('needs') or 0, proposals.get('picked') or 0
        label = f'Build the proposal — {picked} of {needs} lines recommended' if needs else 'Build the proposal'
        s.add('build_proposal', label)
    if latest:
        s.add('issue_proposal', f'Proposal issued (v{latest["version"]})', state='done', since=latest.get('issued_at'))
        _selection(s, latest, sit)
        s.add('mark_sold', 'Mark the winning plan sold')
    elif built:
        s.add('issue_proposal', 'Issue the proposal to the client')
        s.add('mark_sold', 'Mark the winning plan sold', state='blocked', blocked_by='issue_proposal',
              reason=AFTER_ISSUED)  # fmt: skip
    else:
        s.add('issue_proposal', 'Issue the proposal to the client', state='blocked', blocked_by='build_proposal',
              reason=AFTER_BUILT)  # fmt: skip
        s.add('mark_sold', 'Mark the winning plan sold', state='blocked', blocked_by='issue_proposal',
              reason=AFTER_ISSUED)  # fmt: skip


def _selection(s, latest, sit):
    wait = rules.FOLLOW_UP_DAYS['decision']
    issued_at = latest.get('issued_at')
    days = days_since(issued_at, sit.today) or 0
    if days >= wait:
        label = f'Follow up on the proposal — issued {rules.days(days)} ago, nothing sold yet'
        due = local_day(issued_at) + timedelta(days=wait)
        s.add('follow_up_selection', label, severity='warn', since=issued_at, wait_days=wait, due=due)
    else:
        s.add('follow_up_selection', f"Waiting on the client's plan pick — issued {rules.days(days)} ago",
              state='waiting', owner='client', since=issued_at, wait_days=wait)  # fmt: skip


def _commission(s, facts):
    unrated = (facts.get('commission') or {}).get('unrated') or []
    if unrated:
        n = len(unrated)
        s.add('commission', f'Enter the commission for {rules.plural(n, "sold line")}', severity='warn', basis=unrated)
    else:
        s.add('commission', 'Commission entered', state='done')
