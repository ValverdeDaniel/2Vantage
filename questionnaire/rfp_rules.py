"""What the RFP sends of a questionnaire, and to whom (plan.md §9.11; G110, G112, G113). Pure: the RFP passes the
carriers, lines and funding it holds; rfp (slice 46) reads these, so the packet's default ticks and each carrier's
draft share one rule.

- `takes(form, carrier)`: whether a carrier receives this form. A medical form names its audience in `rfp_carriers`
  (`deals/carriers.py` keys); one that names none is Florida Blue's own, which only Florida Blue takes. A carrier
  typed into "Other carriers" (`None`) takes a form with a declared audience (Warner's, which every carrier but
  Florida Blue takes) and never Florida Blue's own. The stop-loss disclosure lists claimants: it goes only to a known
  medical carrier, who quotes the funding it is for, never an ancillary or a typed-in one.
- `disclosure_needed(lines, funding)`: the disclosure rides only when the request asks for stop-loss, level-funded or
  ASO quotes; a fully insured request has no use for a claimant list.
- `copy_to_send(signed_document, paper)`: which copy of a form goes — the filed signed copy, else a paper copy a
  person accepted, else the DRAFT with a warning. A paper copy marked wrong never goes (N5's fix).
- `two_copies(ticked)`: two ticked copies of one form warn (a DRAFT and a paper copy could both go out, N5).
- `changed_since(sent, now)`: what the RFP stored at send (`selectors.rfp.sent_with`: the signed copy's id, else a
  hash of the printed values) against the same now (G113).
Ported from old Vantage 891f1b3 (`market/rfp.questionnaire_takes`, `stop_loss_quoted`, `stop_loss_takes`;
`serializers/pipeline._doc_default_include`).
"""

from deals import carriers

FLORIDA_BLUE = 'florida_blue'
DISCLOSURE_FUNDING = frozenset({'level_funded', 'aso'})
SIGNED, PAPER, DRAFT = 'signed', 'paper', 'draft'
DRAFT_WARNING = 'Not signed by the employer yet: the DRAFT goes out.'
TWO_COPIES = 'Two copies of the {label} are ticked: send one.'


def takes(form, carrier):
    if form['kind'] == 'stop_loss':
        return bool(carrier) and (carriers.BY_KEY.get(carrier) or {}).get('group') == carriers.MEDICAL
    wanted = form.get('rfp_carriers')
    if wanted is None:
        return carrier == FLORIDA_BLUE
    return carrier is None or carrier in wanted


def disclosure_needed(lines, funding):
    return 'stop_loss' in (lines or ()) or bool(DISCLOSURE_FUNDING & set(funding or ()))


def copy_to_send(signed_document, paper):
    """{copy: signed|paper|draft, document: id or None, warning}. `paper`: [{id, review_state}] of the form's kind,
    newest first."""
    if signed_document:
        return {'copy': SIGNED, 'document': signed_document, 'warning': ''}
    accepted = next((doc['id'] for doc in paper if doc.get('review_state') == 'accepted'), None)
    if accepted:
        return {'copy': PAPER, 'document': accepted, 'warning': ''}
    return {'copy': DRAFT, 'document': None, 'warning': DRAFT_WARNING}


def two_copies(ticked):
    """[sentence] for every form ticked twice: `ticked` is [{form, label}] of the packet's ticked copies."""
    seen, out = {}, []
    for entry in ticked:
        seen.setdefault(entry['form'], []).append(entry)
    for entries in seen.values():
        if len(entries) > 1:
            out.append(TWO_COPIES.format(label=entries[0]['label']))
    return out


def changed_since(sent, now):
    """Whether the form changed since it was sent: a different signed copy, or different printed values."""
    if not sent:
        return False
    if sent.get('document'):
        return sent.get('document') != now.get('document')
    return sent.get('hash') != now.get('hash') or bool(now.get('document'))
