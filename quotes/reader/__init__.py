"""The quote reader (plan.md §10.4; D46–D67, D115–D118, F138, F143; slice 18): quotes' half of a Claude read.

`ai/reading.py` cuts the files into ranges and calls Claude with this reader's `prompt.PROMPT` and `schema.SCHEMA`;
the answers come back here: `merge` joins them in reading order, `changes.build_changes` matches them to the deal's
plans and proposes the change set (each value found in its file first), and it waits for review. A person uses it
through `services.read_apply.apply` (the parts they chose, `choice.py`; slice 19) and takes it back with
`revert_read.undo` (↶ Undo this run). `corpus` and `score` are the Eval lane's (`manage.py reader_eval`).
"""

from documents import kinds as document_kinds

READS = ('quote', 'renewal', 'stop_loss_quote', 'tpa_proposal')  # every proposal-bucket kind but SBCs and templates


def reader():
    from ai.registry import Reader

    from .. import revert_read
    from ..services import read_apply
    from . import changes, corpus, merge, prompt, schema, score

    return Reader(
        target='quotes',
        kinds=READS,
        prompt=prompt.PROMPT,
        schema=schema.SCHEMA,
        version=schema.VERSION,
        note=prompt.note,
        merge=merge.merge,
        build_changes=changes.build_changes,
        apply=read_apply.apply,
        undo=revert_read.undo,
        corpus=corpus.cases,
        score=score.score,
        labels={kind: document_kinds.label(kind) for kind in READS},
    )


def register():
    from ai.registry import register_reader

    register_reader(reader())
