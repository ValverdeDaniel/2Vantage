"""The questionnaires on a link's page (plan.md §7.14, §8.20; G83–G98, L91; OQ84, OQ85; slice 58). Allowlisted: one
card per form the link asks, in the request's order (`asked.forms`, waived forms dropped, G83):

{form, title, subtitle, kind, version, mode online|upload, narrowed, blank, signed {name, signed_at} | None, locked,
 sign {label, attestation} | None, state | None, file {accept, received [{name, at}]} | None}

- `state` (a form asked online) is the link's view of it (`questionnaire.selectors.portal.state`): values and bases,
  rows with `mine`, the tables and slots on screen, blanks, option keys, progress, the broker's slots (read-only,
  G86) and the slots a colleague answered. Never a source, a reviewer, a staff name, or an answer another link gave
  on a blank link. The spec (questions, options) is its own cacheable read (`questionnaires/{form}/spec/`).
- `sign` while the whole form is asked online and nobody signed for the officer (G93): the sign box's words and the
  attestation it signs (the form's signature section's own text, shown beside the box). A narrowed ask takes no
  signature and no file (G22).
- `file` (G90, G92): the paper copy, when the form is asked as a signed copy or whole online and unsigned: its slot is
  `qform:<form>`, and only the files received through this request are named (a blank link: its own), never a staff
  upload or a file marked wrong.
- `blank`: the carrier's blank PDF can be viewed and downloaded (G84), on a form that has one and is asked whole.
"""

from documents import kinds
from documents.models import Document
from questionnaire import forms
from questionnaire.selectors import portal

from .asked import PAPER, UPLOAD, takes_paper

SIGN_LABELS = {
    forms.MEDICAL: 'Type your full name to sign as the authorized company officer. This locks the form.',
    forms.STOP_LOSS_KIND: 'Type your full name to sign as the plan sponsor’s authorized officer. This locks the form.',
}


def attestation(form):
    """The signature section's own text: what the officer agrees to (old `signatureIntro`)."""
    found = next((s for s in form['sections'] if str(s.get('key', '')).startswith('signature')), None)
    return (found or {}).get('intro') or ''


def slot_of(form_key):
    return f'{PAPER}{form_key}'


def received(link_ids, slot):
    """[{name, at}] of the paper copies received through `link_ids`, oldest first; never one marked wrong (B11)."""
    found = (
        Document.objects.filter(link_id__in=link_ids, source='client', slot=slot)
        .exclude(review_state='wrong')
        .order_by('uploaded_at', 'id')
        .values_list('original_name', 'uploaded_at')
    )
    return [{'name': name, 'at': at.isoformat()} for name, at in found]


def _signed(row):
    if row is None or row.officer_signed_at is None:
        return None
    return {'name': row.officer_name, 'signed_at': row.officer_signed_at.isoformat()}


def card(ask, shown_links):
    whole = forms.FORMS[ask.form]
    row = ask.view.row if ask.view is not None else None
    locked = bool(row and row.locked)
    online_whole = ask.view is not None and not ask.narrowed
    paper = takes_paper(ask)
    file_kind = forms.FILE_KIND[whole['kind']]
    slot = slot_of(ask.form)
    return {
        'form': ask.form,
        'title': whole['title'],
        'subtitle': whole['subtitle'],
        'kind': whole['kind'],
        'version': whole['version'],
        'mode': ask.mode,
        'narrowed': ask.narrowed,
        'blank': bool(whole.get('blank_pdf')) and not ask.narrowed,
        'signed': _signed(row),
        'locked': locked,
        'sign': (
            {'label': SIGN_LABELS[whole['kind']], 'attestation': attestation(whole)}
            if online_whole and not locked
            else None
        ),
        'state': portal.state(ask.view) if ask.view is not None else None,
        'file': (
            {'slot': slot, 'accept': kinds.BY_KEY[file_kind]['accept'], 'received': received(shown_links, slot)}
            if paper or ask.mode == UPLOAD
            else None
        ),
    }


def section(found, shown_links):
    """[card] for the forms the link asks, or [] when it asks none."""
    return [card(ask, shown_links) for ask in found.forms]


def rail_items(cards):
    """The to-do rail's rows, one per form (G95, L81): done once the officer signed it, a narrowed ask once every
    question it holds is answered, a signed copy once one came."""
    out = []
    for one in cards:
        item = {'key': f'questionnaire_{one["form"]}', 'kind': 'questionnaire', 'label': one['title']}
        if one['state'] is not None:
            progress = one['state']['progress']
            done = bool(one['signed']) or (one['narrowed'] and progress['filled'] >= progress['total'])
            item.update(filled=progress['filled'], total=progress['total'], done=done, narrowed=one['narrowed'])
        else:
            item.update(done=bool(one['signed']) or bool((one['file'] or {}).get('received')))
        out.append(item)
    return out


def stamp(request):
    """What moves the page's `form_stamp` for its forms (G97): an officer's signature or a reopen, so a colleague's open
    page re-reads a form that was signed meanwhile."""
    from questionnaire.models import Questionnaire

    keys = [entry.get('form') for entry in (request.asks or {}).get('questionnaires') or []]
    if not keys:
        return ''
    found = Questionnaire.objects.filter(deal_id=request.deal_id, form__in=keys).order_by('form')
    return '|'.join(f'{form}:{signed or ""}' for form, signed in found.values_list('form', 'officer_signed_at'))
