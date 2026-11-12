"""Every write to a questionnaire (plan.md §6.8, §7.9; G.6 `services/`; OQ9 d), one module per responsibility:

- `answers`: `set_answers`, the tab's answers (typed, or relayed "From the client — entered by us"), with `cleared`;
- `rows`: `add_row`, `remove_row` — stable row ids, min and max (G43);
- `signing`: `sign` (officer or agent; the officer's locks the form) and `reopen` with a reason (G49–G55);
- `picks`: `choose_form`, the checklist item's form choice (G2, G4, G9, G133);
- `marks`: `mark_answers`, approve / ignore / needs checking / clear (E103).
`common` holds the locks (the Deal, intake's row for a choice, then the Questionnaire row), the first write's row and
the Activity helpers. Each write runs in one transaction, records Activity (area `questionnaire`) and returns only
what changed; a write that changes nothing writes nothing.
"""

from .answers import set_answers
from .marks import mark_answers
from .picks import choose_form
from .rows import add_row, remove_row
from .signing import reopen, sign

__all__ = ['add_row', 'choose_form', 'mark_answers', 'remove_row', 'reopen', 'set_answers', 'sign']
