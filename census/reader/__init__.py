"""The census reader (plan.md §10.4, §10.5, §10.8; C11, C19, D29, D109, D110; slice 51): census's half of a Claude read.

A census file sent to Claude (Work with Claude's drawer on the Census tab, a send's census files, "Scan the census with
Claude ▸", "Not our template? Read it with Claude ▸") is read by `ai/reading.py` with this reader:
- a spreadsheet stays out of Claude's reach (`local`): the importer reads it, the offline mapper proposes its columns
  and the mapping assist proposes the ones it left, from their shapes only (D109);
- PDF pages and pictures are read whole by Claude (`prompt`, `schema`), every person in printed order; `merge` keeps a
  person read twice once and puts each dependent under its printed employee;
- `changes.build_changes` stages the people as a proposed `CensusImport` pointing at the job, and the change set only
  points at it (D29). The Census tab shows it in its mapping dialog, dry run and Apply; Apply there uses the read too,
  and the read's Discard sets the import aside (`services.reads`).
It always waits (O.3.3) and registers only while the PHI-gate switch is on (§10.8, §11.4 item 7).
"""

from documents import kinds as document_kinds

READS = ('census',)


def reader():
    from ai.registry import Reader

    from ..services import reads
    from . import changes, local, merge, prompt, schema

    return Reader(
        target='census',
        kinds=READS,
        prompt=prompt.PROMPT,
        schema=schema.SCHEMA,
        version=schema.VERSION,
        note=prompt.note,
        merge=merge.merge,
        build_changes=changes.build_changes,
        must_review=True,
        apply=reads.reader_apply,
        undo=reads.reader_undo,
        discard=reads.reader_discard,
        local=local.local,
        empties=True,
        labels={kind: document_kinds.label(kind) for kind in READS},
    )


def register():
    """Register the reader; left out while the PHI-gate switch is off. Returns whether it registered."""
    from ai.registry import register_reader

    return register_reader(reader())
