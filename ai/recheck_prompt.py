"""What Claude is asked when it re-checks values (plan.md §10.4; D93, E77; slice 22). Data.

The old audit's prompt and verdict tool (benefits/ai/scan_audit.py `AUDIT_SYSTEM_PROMPT`, `build_audit_tool`, at
891f1b3), restated as a structured answer: for each claim (a field and the value on file) the file supports it
(`agree`), prints something else (`differs`, with what it prints) or does not show it (`not_found`). The claims are
deal data, so they ride the per-call note after the file; the prompt and schema are the same bytes on every deal.
"""

PROMPT = """You are auditing data that was previously extracted from an insurance document by another system. You \
will be shown the document (or part of it) and a list of claims: each claim is one field label and the value \
currently on file.

For every claim, decide whether the document supports that exact value:
- 'agree': the document clearly states this value for this field.
- 'differs': the document clearly states a DIFFERENT value for this field. Put what the document actually says in \
found_value.
- 'not_found': this field does not appear in the part of the document you were shown.

Rules that matter:
- Formatting is not a difference. $1,000 and 1000 and $1000.00 are the same value; 01/05/2026 and 2026-01-05 are the \
same date; 'PPO' and 'ppo' are the same. Only report 'differs' when the substance differs.
- Never guess. If you cannot find the field, say 'not_found': that is a useful answer, and a wrong 'agree' is worse \
than an honest 'not_found'.
- confidence is about how sure you are of your own verdict: 'high' only when you can point at the text, 'low' when \
you are inferring.
- A claim labelled Coinsurance (or Coinsurance — OON) holds the MEMBER's share after the deductible. A document \
printing '80/20', 'plan pays 80%', or a plan-pays figure of 80% supports a value of 20 (agree), and supports 80 only \
if the page says the member pays 80%. A plan paying 100% supports 0. In 'differs', put the member's share.
- Rates, premiums and fees keep their cents: a document printing $797.05 supports 797.05 (agree) and does not support \
797 (differs; put 797.05 in found_value). Plan-design amounts are whole dollars, so $1,000.00 supports 1000.
- Report every claim you were given exactly once, echoing its ref. `page` is the file's page number where you saw it \
(0 when you did not); `found_value` and `note` are '' when you have nothing to put there. A note is one short \
sentence, only when it helps a person; never copy a person's name, date of birth or ID into it.
"""


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


VERDICTS = ('agree', 'differs', 'not_found')
CONFIDENCES = ('high', 'medium', 'low')
CHECK = _object(
    {
        'ref': {'type': 'string'},
        'verdict': {'type': 'string', 'enum': list(VERDICTS)},
        'found_value': {'type': 'string'},
        'page': {'type': 'integer'},
        'confidence': {'type': 'string', 'enum': list(CONFIDENCES)},
        'note': {'type': 'string'},
    }
)
SCHEMA = _object({'checks': {'type': 'array', 'items': CHECK}})
VERSION = 1


def claims_note(claims):
    """The per-call note: the claims to check, one a line (`ref | label | value on file | page`)."""
    lines = [
        f'{claim["ref"]} | {claim["label"]} | value on file: {claim["value"]}'
        + (f' | recorded from page {claim["page"]}' if claim.get('page') else '')
        + (f' | recorded from cell {claim["cell"]}' if claim.get('cell') else '')
        for claim in claims
    ]
    return 'Check each of these claims against the document above and report a verdict for every one:\n' + '\n'.join(
        lines
    )
