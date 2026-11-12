"""The packet's questionnaires, issued proposal and attachments (plan.md §8.12, §9.10; K43, K45, K49; G110–G112;
OQ66, OQ68, OQ69). Pure over one request (`context.Request`). Words from old Vantage 891f1b3
`serializers/pipeline.py` and `CarriersTab.jsx`.

- **Questionnaires & disclosures** (K43): one row per form the deal uses, from `questionnaire.selectors.rfp.rfp_files`:
  the copy that goes (`copy_to_send`: the filed signed copy, else an accepted paper copy, else the DRAFT with
  "Not signed by the employer yet"), the default tick by who is asked (`takes`) and what is asked
  (`disclosure_needed`), with the reason when it is off. A kind with no form set up shows "Not set up" and points to the
  readiness checklist's picker (K45, K15).
- **Client proposal** (OQ68, J169): the latest issued proposal, off on purpose (it shows each carrier the others'
  pricing); unavailable until one is issued. The comparison workbook, stop-loss workbook, benefit guide and
  contribution model leave the RFP (K48).
- **Attachments** (K49): live files only. Renewal (kind renewal, or a quote filed as the renewal), claims (on at 100+
  enrolled or when a line in force is level- or self-funded), the invoice (off on purpose), SBCs (current or renewal
  on; another carrier's plan off on purpose; no role listed, unticked, "Role not set": OQ69) and paper questionnaires
  and disclosures (off on purpose once the in-app form is signed; a paper disclosure follows the funding asked). A
  paper copy the questionnaire row already sends is not listed twice. Files carrying member data are marked `phi`.
"""

from documents import kinds
from documents.services import access
from questionnaire import forms as questionnaire_forms
from questionnaire import rfp_rules

from . import base

PROPOSAL = 'proposal'
COMPETITOR = 'Shows each carrier the other carriers’ pricing'
NO_PROPOSAL = 'No proposal has been issued on this deal yet'
INVOICE_OFF = 'Our own census-vs-billing check, not something carriers ask for'
ALTERNATES_OFF = 'Another carrier’s plan'
NO_ROLE = 'Role not set'
SIGNED_PAPER_OFF = 'The signed in-app form goes instead'
NOT_ASKED = 'This request asks for no level-funded, self-funded or stop-loss quotes'
PAPER_KINDS = {'questionnaire': questionnaire_forms.MEDICAL, 'stop_loss': questionnaire_forms.STOP_LOSS_KIND}
COPY_WORDS = {
    rfp_rules.SIGNED: 'The signed copy, as filed in Documents.',
    rfp_rules.PAPER: 'The copy signed on paper, as filed in Documents.',
    rfp_rules.DRAFT: 'Filled from the Questionnaire tab, marked DRAFT until the officer signs.',
}
NOT_SET_UP = {
    questionnaire_forms.MEDICAL: (
        'Medical questionnaire',
        'No carrier form is set up on this deal. Groups of 51+ default to Florida Blue’s; any deal can be given one '
        'on the readiness checklist',
    ),
    questionnaire_forms.STOP_LOSS_KIND: (
        'Stop-loss disclosure',
        'The SIIA disclosure is opt-in: set it up on the readiness checklist’s stop-loss row when a reinsurance quote '
        'needs it',
    ),
}
QUESTIONNAIRE_SIZE = 400_000  # about what a filled form adds to an email when it is built, not filed (K121)


def file_key(form_key):
    kind = questionnaire_forms.FORMS[form_key]['kind']
    return f'{"disclosure" if kind == questionnaire_forms.STOP_LOSS_KIND else "questionnaire"}-{form_key}'


def questionnaires(ctx):
    out = []
    for entry in ctx.forms:
        form = questionnaire_forms.FORMS[entry['form']]
        filed = ctx.form_documents.get(entry['document'])
        out.append(
            base.card(
                file_key(entry['form']),
                'questionnaires',
                entry['label'],
                'pdf',
                default=entry['include'],
                reason=entry['reason'],
                hint='' if entry['signed'] or entry['copy'] == rfp_rules.PAPER else 'Not signed by the employer yet',
                sub=COPY_WORDS[entry['copy']],
                form=entry['form'],
                form_kind=form['kind'],
                copy=entry['copy'],
                document=entry['document'],
                phi=True,
                size=filed.size if filed else QUESTIONNAIRE_SIZE,
            )
        )
    return out


def notices(ctx):
    """ "Not set up" for each kind of form the deal has none of (K45), with the forms its picker offers."""
    armed = {questionnaire_forms.FORMS[entry['form']]['kind'] for entry in ctx.forms}
    out = []
    for kind, (title, text) in NOT_SET_UP.items():
        if kind in armed:
            continue
        names = [questionnaire_forms.FORMS[key]['title'] for key in questionnaire_forms.forms_of(
            questionnaire_forms.ITEM_OF_KIND[kind])]  # fmt: skip
        tail = f' — {" · ".join(names)}.' if names else '.'
        out.append({'kind': kind, 'title': title, 'text': f'{text}{tail} A copy signed on paper rides under '
                                                         'Attachments instead.'})  # fmt: skip
    return out


def proposal(ctx):
    issued = ctx.issued
    return base.card(
        PROPOSAL,
        'documents',
        'Client proposal',
        kinds.extension(issued.original_name).lstrip('.') if issued else 'pdf',
        default=False,
        deliberate=COMPETITOR,
        available=issued is not None,
        reason='' if issued else NO_PROPOSAL,
        sub=f'The latest issued: {issued.label or issued.original_name}' if issued else '',
        document=issued.id if issued else None,
        size=issued.size if issued else 0,
    )


def _sent_paper(ctx):
    return {entry['document'] for entry in ctx.forms if entry['copy'] == rfp_rules.PAPER}


def _attachment_tick(ctx, doc, signed):
    """(default, deliberate, reason) for one attachment."""
    if doc.kind == 'invoice':
        return False, INVOICE_OFF, ''
    if doc.kind == 'sbc':
        if doc.role == 'alternates':
            return False, ALTERNATES_OFF, ''
        return (True, '', '') if doc.role in ('current', 'renewal') else (False, '', NO_ROLE)
    if doc.kind == 'claims':
        return ctx.count is not None and ctx.count >= 100 or ctx.self_funded, '', ''
    if doc.kind in PAPER_KINDS:
        if signed.get(PAPER_KINDS[doc.kind]):
            return False, SIGNED_PAPER_OFF, ''
        if doc.kind == 'stop_loss' and not rfp_rules.disclosure_needed(ctx.lines, ctx.funding):
            return False, '', NOT_ASKED
    return True, '', ''


def attachments(ctx):
    signed = {}
    for entry in ctx.forms:
        kind = questionnaire_forms.FORMS[entry['form']]['kind']
        signed[kind] = signed.get(kind, False) or entry['signed']
    already = _sent_paper(ctx)
    out = []
    for doc in ctx.documents:
        if doc.kind == 'quote' and doc.role != 'renewal' or doc.id in already:
            continue
        default, deliberate, reason = _attachment_tick(ctx, doc, signed)
        label = doc.label or (kinds.label('renewal') if doc.kind == 'quote' else kinds.label(doc.kind))
        pages = f' · {doc.page_count} page{"" if doc.page_count == 1 else "s"}' if doc.page_count else ''
        out.append(
            base.card(
                f'doc-{doc.id}',
                'attachments',
                label,
                kinds.extension(doc.original_name).lstrip('.') or 'file',
                default=default,
                deliberate=deliberate,
                reason=reason,
                available=bool(doc.file),
                sub=f'{access.download_name(doc)}{pages}',
                document=doc.id,
                doc_kind=doc.kind,
                lines=list(doc.lines or []),
                phi=access.carries_members(doc),
                size=doc.size or 0,
            )
        )
    return out
