"""The Review tab's own counts (plan.md §8.8; O.6 #3; L1, L13, L28, L49). Pure, over one deal's `summary.facts`.

One rule, so the tab's pills, the tray (slice 56) and the shell's badges (slice 61) can never disagree:
- `to_send`: asks and send-backs waiting in the tray (the Request pill's "N to send"; drafts are ours, never the
  client's, so they never join Waiting);
- `to_review`: what came back and waits on us: client answers pending on the owners' rows, people a client added,
  client files nobody has accepted or marked wrong, and the client's open questions (the Review pill). The AI reads'
  counts join with the To review lane (L9, L10; slice 55);
- `waiting`: the Waiting lane's count, the requests still out plus the links whose person is still answering;
- `questions`: the client's questions nobody has answered (the "?" mark).
"""


def counts(facts):
    """{to_send, to_review, waiting, questions} from one deal's facts (`review.summary.facts`)."""
    facts = facts or {}
    pending = facts.get('pending') or {}
    questions = (facts.get('questions') or {}).get('open', 0)
    return {
        'to_send': facts.get('tray', 0),
        'to_review': pending.get('total', 0) + questions,
        'waiting': len(facts.get('waiting') or []) + len(facts.get('in_progress') or []),
        'questions': questions,
    }
