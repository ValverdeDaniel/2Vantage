"""The deal's own problems, whatever the file (plan.md §5.7; K19, K73, K122, L120). Reads one request's facts.

- `no_owner` (K122, bug 19): with no owner, the files print the agent of record or the agency's producer, and the
  carriers reply to the agency's returns inbox or nowhere (OQ65).
- `ai_open`: census values Claude doubted (or a person flagged) that nobody has looked at (`documents.review_rules.
  open_warning`, the one rule; OQ28: a count, never a block).
- The providers' lines (`providers`, slice 55): the client's census answers the review app registers (L120: not
  reviewed, still typing, going back): the file prints approved values only (OQ85), so it leaves them out until they
  are accepted. Before slice 55 rfp stood in for them with the census's stored pending count.
- `enrollment` (K19): when intake, the census and the Advisor disagree about how many are enrolled, every file that
  prints the count (the forms, the cover, UHC's group tab) says so, naming the one it printed.
"""

from documents.review_rules import open_warning

from . import providers
from .problems import plural, problem


def _open_reads(people):
    return sum(1 for person in people for entry in (person.get('sources') or {}).values() if open_warning(entry))


def problems(ctx, counted=False):
    out = []
    if ctx.deal.owner_id is None:
        agent = ctx.agent or 'no agent'
        reply = ctx.return_to or 'no address (set the returns inbox in Django admin)'
        text = f'No owner on this deal: the files print {agent} as the agent, and carriers reply to {reply}.'
        out.append(problem('no_owner', text))
    doubted = _open_reads(ctx.people)
    if doubted:
        text = (
            f'{doubted} census {plural(doubted, "value", "values")} Claude was unsure of or someone flagged '
            f'{plural(doubted, "has", "have")} not been checked.'
        )
        out.append(problem('ai_open', text, doubted, fix={'tab': 'census'}))
    out += providers.problems(ctx.deal)
    if counted and ctx.check.get('differ') and ctx.check.get('warning'):
        out.append(problem('enrollment', ctx.check['warning'], fix={'tab': 'intake'}))
    return out
