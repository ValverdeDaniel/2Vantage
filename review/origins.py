"""Where a value came from, in the boards' words (plan.md §3.7; C27, B37, L16; D-060; old 891f1b3
`reviewrequest/originWords.js`). A data module: served by /api/meta/ `review.origins` (rule 1), read by the Intake and
Census boards' origin bars and chips.

`origin_of(source, waiting=False)`: a stored value's source (`deals.values.source`) as one of these keys; `waiting`
for a client answer not approved yet.
"""

ORIGINS = [
    {'key': 'ai', 'label': 'Read by AI', 'short': 'read by AI', 'tone': 'ai'},
    {'key': 'import', 'label': 'From their spreadsheet', 'short': 'from their file', 'tone': 'file'},
    {'key': 'waiting', 'label': 'From the client — waiting for approval', 'short': 'from the client, waiting',
     'tone': 'client'},
    {'key': 'client', 'label': 'From the client — approved', 'short': 'from the client, approved', 'tone': 'client'},
    {'key': 'relay', 'label': 'From the client — entered by us', 'short': 'from the client, typed by us',
     'tone': 'client'},
    {'key': 'typed', 'label': 'Typed by us', 'short': 'typed by us', 'tone': 'us'},
    {'key': 'prefill', 'label': 'Filled in from the deal', 'short': 'from the deal', 'tone': 'other'},
    {'key': 'other', 'label': 'On file — origin not recorded', 'short': 'not recorded', 'tone': 'other'},
]  # fmt: skip
KEYS = tuple(origin['key'] for origin in ORIGINS)
FROM = {'ai': 'ai', 'import': 'import', 'client': 'client', 'relay': 'relay', 'typed': 'typed', 'prefill': 'prefill'}


def origin_of(source, *, waiting=False):
    if waiting:
        return 'waiting'
    return FROM.get((source or {}).get('origin') if isinstance(source, dict) else None, 'other')
