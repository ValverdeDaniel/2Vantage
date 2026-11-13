"""The owners review decides through (plan.md §5.8; O.3.4: "a plain table of these modules"; L.6 "the owner contract").

Each owner module offers `approve_client`, `reject_client` and `revert_approval` (user, deal_id, slots) → Decided(slots,
[Activity rows]); review never writes an owner's row itself (rule 3). Listed in chain order, the order a decision
locks and writes them in (O.3.7). The questionnaire joined with slice 58 (its slots are (form, slot)).
"""

from census.services import approvals as census
from intake.services import approvals as intake
from questionnaire.services import approvals as questionnaire

OWNERS = {'intake': intake, 'census': census, 'questionnaire': questionnaire}
