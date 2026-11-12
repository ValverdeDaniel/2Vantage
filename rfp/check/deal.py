"""The deal's own problems, whatever the file (plan.md §5.7; K19, K73, K122). Reads one request's facts.

- `no_owner` (K122, bug 19): with no owner, the files print the agent of record or the agency's producer, and the
  carriers reply to the agency's returns inbox or nowhere (OQ65).
- `ai_open`: census values Claude doubted (or a person flagged) that nobody has looked at (`documents.review_rules.
  open_warning`, the one rule; OQ28: a count, never a block).
- `client_waiting`: census answers the client sent that nobody has reviewed: the file prints the approved values only
  (OQ85), so it leaves those out until they are accepted.
- `enrollment` (K19): when intake, the census and the Advisor disagree about how many are enrolled, every file that
  prints the count (the forms, the cover, UHC's group tab) says so, naming the one it printed.
The client-link states the old check also counted ("still typing", "sent back") belong to the review app, right of
rfp; until it registers a counter, the census's pending answers stand for them.
"""

from documents.review_rules import open_warning

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
    waiting = ctx.census['pending_answers'] + ctx.census['pending_people']
    if waiting:
        text = (
            f'{waiting} census {plural(waiting, "answer", "answers")} the client sent {plural(waiting, "is", "are")} '
            f'waiting for review — the file leaves {plural(waiting, "it", "them")} out until accepted.'
        )
        out.append(problem('client_waiting', text, waiting, fix={'tab': 'census'}))
    if counted and ctx.check.get('differ') and ctx.check.get('warning'):
        out.append(problem('enrollment', ctx.check['warning'], fix={'tab': 'intake'}))
    return out
