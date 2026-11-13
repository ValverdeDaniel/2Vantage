"""Where one item stands on the request page's ask list (plan.md §8.8; L29; old 891f1b3 `RequestRail.jsx` STATUS,
`request_page.py` `_status`). Pure: one function over what the tray, the asks out, the owners' entries and the notes
say about the item, so the rail, its counts and the Show chips can never disagree (L.6: "Status is one pure function
over asks, drafts, entries and notes").

`status(question=, draft=, pending=, asked=, filled=)`, in this order: a client question nobody answered
(`question`), waiting in the tray (`in_cart`), an answer from the client waiting for review (`answered`), out with the
client on a link that opens (`asked`), something on file (`on_file`), else `missing`.
`counts(items)` → {all, question, in_cart, answered, asked, on_file, missing}: the Show chips' numbers.
"""

QUESTION, IN_CART, ANSWERED, ASKED, ON_FILE, MISSING = 'question', 'in_cart', 'answered', 'asked', 'on_file', 'missing'
STATUSES = (QUESTION, IN_CART, ANSWERED, ASKED, ON_FILE, MISSING)


def status(*, question=False, draft=False, pending=False, asked=False, filled=False):
    if question:
        return QUESTION
    if draft:
        return IN_CART
    if pending:
        return ANSWERED
    if asked:
        return ASKED
    return ON_FILE if filled else MISSING


def counts(items):
    out = {key: 0 for key in STATUSES}
    for item in items:
        out[item['status']] += 1
    return {'all': len(items), **out}
