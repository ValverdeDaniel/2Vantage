"""What the census screens read (plan.md §7.7). Reads only; nothing here writes.

- `page`: the census page — the stored summary and rollup, validation and missing cells on read, one page of people;
- `imports`: an import's light row, and the mapping dialog's payload with samples read from the file for that answer;
- `roster`: one person as the grid draws them, a hand edit's answer (C6) and the roster's required blanks (C24).
"""

from .imports import import_payload, import_row
from .page import census_page
from .roster import member_answer, missing_refs

__all__ = ['census_page', 'import_payload', 'import_row', 'member_answer', 'missing_refs']
