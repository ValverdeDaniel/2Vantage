"""Why we recommend it, for one line (plan.md §8.14; J57, J.5 B7; old Vantage 891f1b3 `proposal_pdf._why_for`). Pure.

One rule for every file (the PDF, the PowerPoint's notes, the spreadsheet's cover): a line's own words
(`reasons.<line>`), else the deal-wide words (`recommendation`) only when no line has words of its own, so a sentence
about medical never prints under dental. The deal-wide words also stay in the at-a-glance notes. The files call it
from slice 27 on.
"""


def _words(text):
    return (text or '').strip() if isinstance(text, str) else ''


def why_for(config, line):
    """The words to print under `line`'s recommendation ('' for none). `config`: the stored proposal config."""
    by_line = (config or {}).get('reasons') or {}
    own = _words(by_line.get(line)) if line else ''
    if own:
        return own
    if any(_words(text) for text in by_line.values()):
        return ''
    return _words((config or {}).get('recommendation'))
