"""The questionnaire reader (plan.md §10.4, §10.5, §10.8; D113, G99–G102, G106, G107; slice 52): the questionnaire's
half of a Claude read.

A filled carrier form (a medical questionnaire or a stop-loss disclosure, as a PDF or a picture), sent to Claude from
Work with Claude's drawer or filed on Documents, is read by `ai/reading.py` with this reader:
- `local` refuses before any call when the deal has no form for the file, or that form is signed (G99: a signed
  form is never read into), and lets Claude see the pages whole (a filled form is member data by design, §10.8);
- `prompt` and `schema` are the same bytes for every deal and form (they cache): the three forms' questions, and an
  answer of keyed values and keyed rows; the per-call `note` names the deal's form for the file, never the file;
- `merge` joins the answers per form (the first reading of an answer wins, a different later one is doubted);
- `changes.build_changes` stages the read (`services.reads.stage`) and the job's change set only points at it, with
  counts: no answer reaches a job's result, steps or log (§10.8).
It always waits for a person, who uses it slot by slot from the drawer's card (`services.reads`), and it registers
only while the PHI-gate switch is on (§11.4 item 7), with its `<questionnaire>` context for chats (G106).
"""

from documents import kinds as document_kinds

READS = ('questionnaire', 'stop_loss')  # a medical form's file, a stop-loss disclosure's


def reader():
    from ai.registry import Reader

    from ..services import reads
    from . import changes, local, merge, prompt, schema

    return Reader(
        target='questionnaire',
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
    """Register the reader and its chat context; both are left out while the PHI-gate switch is off. Returns whether
    the reader registered."""
    from ai import registry

    from .. import turn_context

    registered = registry.register_reader(reader())
    if registered:
        registry.register_context('questionnaire', turn_context.provide, order=14)
    return registered
