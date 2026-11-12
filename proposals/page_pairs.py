"""What a column on Pages says and offers about printing two plans as one (plan.md §5.4, §8.14; D-219, J15, F137;
slice 33; the old ProposalPlansCard.jsx `mergeControl` and ProposalPages.jsx's "(one column)" chip at 891f1b3). Pure.

Read over the line as quotes keeps it (both halves, `quotes.pairs`), never the folded one, so a pair is offered and
split whether or not both halves are on the proposal:
- a plan in a stored pair: "⧉ One column with <the other>" and Split;
- a renewal whose current plan is in a pair: "⧉ One column with <the other renewal>", derived, no Split;
- otherwise the plans it can be paired with: the line's other plans of one carrier and one kind (two current plans,
  or two quotes), in no pair already, none of them a renewal that follows a pair.
A folded column also says so beside its name ("+ <the other> (one column)", F137).
"""

from quotes import pairs

PAIRED_TITLE = (
    'The client documents print these two as one column, worked out from both; the Advisor, the grid and Documents '
    'keep both'
)
FOLLOWS_TITLE = 'Its current plan prints as one column, so this renewal does too'
OFFER_TITLE = (
    "Print two plans as one column in the client documents (Florida Blue's 05182 and 05183, say); both stay in the data"
)


def _name(plan):
    return plan.name or plan.words


def _carrier(plan):
    return (plan.carrier or '').strip().lower()  # as typed, as the pairing service checks it


def choices(line, plan):
    """[{id, name}] the plans `plan` may print as one column with, in the line's order."""
    taken = {pid for pair in pairs.stored(line) for pid in pair}
    if plan.id in taken or pairs.follows(line, plan.id):
        return []
    return [
        {'id': other.id, 'name': _name(other)}
        for other in line.plans
        if other.id != plan.id
        and other.id not in taken
        and _carrier(other) == _carrier(plan)
        and (other.role == 'current') == (plan.role == 'current')
        and not pairs.follows(line, other.id)
    ]


def facts(line, plan_id, folded):
    """The column's pair control: {state: paired | follows | open, with_id, with, folded, title, choices}, or None
    when there is nothing to say. `line` is the unfolded LineData; `folded` the ids folded on the pages."""
    plan = line.by_id.get(plan_id)
    if plan is None:
        return None
    partner = pairs.partner(line, plan.id)
    if partner is not None:
        other = line.by_id[partner]
        return {
            'state': 'paired',
            'with_id': other.id,
            'with': _name(other),
            'folded': plan.id in folded,
            'title': PAIRED_TITLE,
            'choices': [],
        }
    follows = pairs.follows(line, plan.id)
    if follows is not None:
        other = line.by_id[follows]
        return {
            'state': 'follows',
            'with_id': other.id,
            'with': _name(other),
            'folded': plan.id in folded,
            'title': FOLLOWS_TITLE,
            'choices': [],
        }
    found = choices(line, plan)
    if not found:
        return None
    return {'state': 'open', 'with_id': None, 'with': '', 'folded': False, 'title': OFFER_TITLE, 'choices': found}
