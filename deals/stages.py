"""Deal stages (plan.md §4.6, §5.1). Pure functions."""

STAGES = [
    ('intake', 'Intake'),
    ('quoting', 'Quoting'),
    ('proposal', 'Proposal'),
    ('sold', 'Sold'),
    ('lost', 'Lost'),
]
LADDER = ['intake', 'quoting', 'proposal', 'sold']
MANUAL = {'intake', 'quoting', 'proposal'}
LABELS = dict(STAGES)


def forward(current, target):
    """The stage after an automatic move: only forward along the ladder; a lost deal stays lost."""
    if current == 'lost' or current not in LADDER or target not in LADDER:
        return current
    return target if LADDER.index(target) > LADDER.index(current) else current


def label(stage):
    return LABELS.get(stage, stage)
