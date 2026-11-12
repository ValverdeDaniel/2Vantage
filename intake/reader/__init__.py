"""The intake reader (plan.md §10.4, §10.5, §10.8; B40, D112; slice 51): intake's half of a Claude read.

A company document the client already has (a current invoice, a plan document, a Form 5500, or anything filed as
"Other": a benefit summary, a completed intake form), sent to Claude from the Intake tab's Work with Claude, is read
by `ai/reading.py` with this reader: Claude records the intake answers it prints, the coverage in force and the
group's contacts (`prompt`, `schema`); `merge` keeps each answer's first reading and flags a different later one;
`changes.build_changes` lists what using it would change, leaving alone what a person stands behind; it always waits
in Intake's review (O.3.3), and `services.read_apply` lands the chosen parts with ↶ Undo this run. Its change set is
emptied once used (D74). It registers only while the PHI-gate switch is on (§10.8, §11.4 item 7), and a send reaches
it only from the Intake tab (`ai.kinds.OWN_TAB_ONLY`).
"""

from documents import kinds as document_kinds

READS = ('other', 'invoice', 'plan_doc', 'form_5500')  # "Other" first: what the Intake tab files a company file as


def reader():
    from ai.registry import Reader

    from ..services import read_apply
    from . import changes, merge, prompt, schema

    return Reader(
        target='intake',
        kinds=READS,
        prompt=prompt.PROMPT,
        schema=schema.SCHEMA,
        version=schema.VERSION,
        note=prompt.note,
        merge=merge.merge,
        build_changes=changes.build_changes,
        must_review=True,
        apply=read_apply.apply,
        undo=read_apply.undo,
        empties=True,
        labels={kind: document_kinds.label(kind) for kind in READS},
    )


def register():
    """Register the reader; left out while the PHI-gate switch is off. Returns whether it registered."""
    from ai.registry import register_reader

    return register_reader(reader())
