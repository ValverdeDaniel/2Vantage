"""Review's lines in rfp's export check (plan.md §8.12; L120, OQ85; old 891f1b3 `export_check.deal_problems`; slice 55),
registered in ReviewConfig.ready() with `rfp.check.providers.register`.

What the client sent on the census and nobody approved yet never prints (OQ85), so a census file leaves it out; the
check says so, as counts, never a value or a name:
- `client_waiting`: answers (and people a client added) ready for review — "not in the file until approved";
- `client_typing`: answers still being typed on a link (not submitted yet, not idle a day);
- `going_back`: answers sent back to the client and not answered since, a send-back still in the tray included
  (`rules.tray.going_back`, slice 56).
The client's questions on a questionnaire are that form's own check (`questionnaire.check`). Fix ▸ opens the review
queue (the census's section first when it holds something).

`stamp(deal)` is the lines' counts, so `checks_stamp` moves when one does (an answer saved, a link submitted, an
answer turning idle) and the page asks for the pills again.
"""

from deals import clock
from rfp.check.problems import plural, problem

from .rules import sections as section_rules
from .selectors import entries as entry_rows
from .selectors import going

FIX = {'tab': 'review', 'view': 'queue'}


def _counts(deal):
    now = clock.now()
    found = entry_rows.waiting([deal.id], ('census',)).get(deal.id, [])
    back = going.refs([deal.id], {deal.id: found}, going.opens_for([deal.id], now))[deal.id]
    return section_rules.counts(found, entry_rows.links_of(found), now, back)['census']


def problems(deal):
    counts = _counts(deal)
    out = []
    waiting, typing = counts['to_review'], counts['in_progress']
    if waiting:
        text = (
            f'{waiting} census {plural(waiting, "answer", "answers")} the client sent '
            f'{plural(waiting, "is", "are")} waiting for review — not in the file until approved.'
        )
        out.append(problem('client_waiting', text, waiting, fix=FIX))
    if typing:
        text = (
            f'The client is still answering {typing} census {plural(typing, "value", "values")} (not submitted yet) — '
            'not in the file until approved.'
        )
        out.append(problem('client_typing', text, typing, fix=FIX))
    back = counts['going_back']
    if back:
        text = (
            f'{back} census {plural(back, "value", "values")} went back to the client and '
            f'{plural(back, "is", "are")} not answered yet.'
        )
        out.append(problem('going_back', text, back, fix=FIX))
    return out


def stamp(deal):
    counts = _counts(deal)
    return [counts['to_review'], counts['in_progress'], counts['going_back']]
