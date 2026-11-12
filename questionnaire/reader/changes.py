"""A questionnaire read's change set: a pointer to what it staged (plan.md §10.5, §10.8; D74, D113, G99; slice 52).

Questionnaire reads always wait for a person (O.3.3). What Claude read waits as a `StagedRead` per form
(`services.reads.stage`), and the job's change set only points at it ("census, intake and questionnaire jobs hold
only a pointer", D.6): one item per form, op `questionnaire_read`, with counts. Nothing in it is an answer, so the
drawer's card, the strip, the job's steps and its log never carry a medical one (§10.8); the card reads the staged
read from the questionnaire's own door. The findings say what the read did in counts.

A read that finds nothing fails (G99, challenge 3). A read that matches the form changes nothing and waits for no one
(D60). A form signed while Claude read is staged all the same and says it cannot be used until the form is reopened
(G99: never applied to a signed form).
"""

from ai.progress import JobFailed

from .. import forms
from ..models import Questionnaire
from ..selectors import context
from . import clean, review

KEPT = ('failed_parts', 'left_out_pages', 'model', 'cost_usd', 'estimate_usd', 'partial', 'halted')
NOTHING = 'No questionnaire answers could be read from this file.'
SIGNED = '{label} was signed while Claude read the file: nothing from it can be used until the form is reopened.'


def _plural(count, one, many):
    return f'{count} {one if count == 1 else many}'


def _findings(label, counts, review_counts):
    said = []
    if counts['not_taken']:
        said.append(f'{_plural(counts["not_taken"], "answer", "answers")} the form does not take were left out.')
    if counts['unknown']:
        said.append(
            f'{_plural(counts["unknown"], "answer", "answers")} named no question of {label} and were left out.'
        )
    if counts['twice']:
        said.append(
            f'{_plural(counts["twice"], "answer was", "answers were")} read two ways: the first is kept, unticked.'
        )
    room = counts['dropped'] + review_counts['no_room']
    if room:
        said.append(f'{_plural(room, "row", "rows")} did not fit on the form and were left out.')
    if review_counts['left_over']:
        said.append(
            f'{_plural(review_counts["left_over"], "row", "rows")} an earlier read of this file added '
            'are not in this read; they stay on the form.'
        )
    return [{'text': text, 'hard': False} for text in said]


def _item(deal, staged, read):
    """The pointer for one staged read, and its findings."""
    row = Questionnaire.objects.filter(deal_id=deal.id, form=staged.form).first()
    view = context.form_view(staged.form, row, context.prefill_facts(deal))
    _listed, counted = review.entries(view, read, staged.document_id)
    label = forms.label(staged.form)
    signed = bool(row and row.locked)
    item = {
        'id': f'form:{staged.form}',
        'op': 'questionnaire_read',
        'read': staged.id,
        'form': staged.form,
        'label': label,
        'tick': not signed,
        'signed': signed,
        'answers': counted['answers'],
        'rows': counted['rows'],
        'conflicts': counted['conflicts'],
    }
    found = _findings(label, read['counts'], counted)
    if signed:
        found.insert(0, {'text': SIGNED.format(label=label), 'hard': False})
    return item, found


def build_changes(deal, user, merged, files, extra):
    """The change set (D.6's shape) of a questionnaire read, after staging what it read."""
    from ..services.reads import counted, stage

    out = {key: extra[key] for key in KEPT if key in extra}
    out.update(v=1, target='questionnaire', documents=sorted({file.id for file in files}))
    cleaned = {key: clean.clean(forms.FORMS[key], read) for key, read in merged.items()}
    if not any(read['counts']['answers'] or read['counts']['rows'] for read in cleaned.values()):
        raise JobFailed(NOTHING)
    items, findings, said = [], [], []
    for key, read in cleaned.items():
        row = Questionnaire.objects.filter(deal_id=deal.id, form=key).first()
        view = context.form_view(key, row, context.prefill_facts(deal))
        if not review.entries(view, read, read['documents'][0])[0]:
            said.append(f'{forms.label(key)}: nothing new')
            continue
        staged = stage(user, deal.id, extra.get('job'), key, read['documents'][0], read)
        item, found = _item(deal, staged, read)
        items.append(item)
        findings += found
        said.append(f'{item["label"]}: {counted(item["answers"], item["rows"])}')
    out['findings'] = findings
    out['items'] = items
    out['counts'] = {
        'answers': sum(item['answers'] for item in items),
        'rows': sum(item['rows'] for item in items),
        'conflicts': sum(item['conflicts'] for item in items),
    }
    if items:
        out['summary'] = f'Read {"; ".join(said)}, ready for review'
    else:
        out['summary'] = 'Nothing new: the form already says what this file says.'
    return out
