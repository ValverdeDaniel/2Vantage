"""The client portal's questionnaire doors (plan.md §7.14; L.6 endpoints; G84, G87, G93, L91; rule 11; slice 58):
`/api/portal/<token>/questionnaires/<form>/…`, public, with the portal's guard, throttles and headers (views.py).

- GET    …/spec/[?v=<version>] → the form as this link asks it (`questionnaire.spec_payload.portal_spec`): the one
  portal answer a browser may keep (`private, max-age`, L.6 Ch. 15), since it holds no answer; 404 a form the link
  does not ask online.
- GET    …/blank/[?inline=1] → the carrier's bundled blank PDF (G84; old `?blank=1`), not logged (it holds nothing of
  the client's); 404 when the form has none, or the link asks it narrowed or not at all.
- POST   …/rows/ {block} → 201 {row_id, state}: "＋ Add another …" (G87).
- DELETE …/rows/<block>/<row_id>/ → {state}: a row their link added, while it holds no approved answer; 409 else.
- POST   …/sign/ {name, sign_anyway?} → {questionnaire: card, link}: the officer's typed signature (G93); 409 {detail,
  incomplete: {filled, total}} for blank required answers (Sign anyway), a lost deal, a form already signed.
404 bad token, 410 gone, 428 PIN needed, 403 a staff session's write (guard.py), like every portal door.
"""

from django.http import Http404
from rest_framework import status
from rest_framework.response import Response

from deals.downloads import file_response
from questionnaire.pdf.build import blank as blank_of
from questionnaire.spec_payload import portal_spec

from ..models import ClientLink
from ..services import forms as form_services
from . import files_part, guard, questionnaire_part, throttles
from .asked import asked
from .views import PortalView, _body, _link_state

SPEC_CACHE = 'private, max-age=3600'
MAX_ROW = 10**6


def _found(opened):
    siblings = list(opened.request.links.values_list('id', flat=True))
    return asked(opened.link, opened.request, opened.deal, link_ids=siblings), siblings


def _ask(opened, form_key):
    found, siblings = _found(opened)
    ask = next((one for one in found.forms if one.form == form_key), None)
    if ask is None:
        raise guard.Unknown()
    return ask, found, siblings


def card(link_id, form_key):
    """The form's card as the page now reads it, after a write."""
    link = ClientLink.objects.select_related('request__deal__client').get(pk=link_id)
    siblings = list(link.request.links.values_list('id', flat=True))
    found = asked(link, link.request, link.request.deal, link_ids=siblings)
    shown = files_part.shown_links(link, siblings)
    return next(one for one in questionnaire_part.section(found, shown) if one['form'] == form_key), link


def states(link_id, form_keys):
    """{form: state} of the forms a save named: the page re-reads what is on screen from it (G20, G25)."""
    if not form_keys:
        return {}
    link = ClientLink.objects.select_related('request__deal__client').get(pk=link_id)
    siblings = list(link.request.links.values_list('id', flat=True))
    found = asked(link, link.request, link.request.deal, link_ids=siblings)
    shown = files_part.shown_links(link, siblings)
    return {one['form']: one['state'] for one in questionnaire_part.section(found, shown) if one['form'] in form_keys}


class SpecView(PortalView):
    throttle_classes = (throttles.Read,)

    def get(self, request, token, form):
        opened = self.open(request, token)
        ask = _ask(opened, form)[0]
        if ask.view is None:
            raise guard.Unknown()
        response = Response(portal_spec(form, ask.picks))
        self.cache = SPEC_CACHE
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if getattr(self, 'cache', '') and response.status_code == 200:
            response['Cache-Control'] = self.cache
        return response


class BlankView(PortalView):
    throttle_classes = (throttles.Read,)

    def get(self, request, token, form):
        opened = self.open(request, token)
        ask = _ask(opened, form)[0]
        path, name = blank_of(form)
        if path is None or ask.narrowed:
            raise guard.Unknown()
        return file_response(path.open('rb'), name, inline=request.query_params.get('inline') == '1')


class RowsView(PortalView):
    def post(self, request, token, form):
        opened = self.open(request, token, write=True)
        row_id = form_services.add_row(opened.link.id, form, _body(request).get('block'))
        found, link = card(opened.link.id, form)
        return Response({'row_id': row_id, 'state': found['state'], 'link': _link_state(link)},
                        status=status.HTTP_201_CREATED)  # fmt: skip


class RowView(PortalView):
    def delete(self, request, token, form, block, row_id):
        opened = self.open(request, token, write=True)
        if row_id > MAX_ROW:
            raise Http404
        form_services.remove_row(opened.link.id, form, block, row_id)
        found, link = card(opened.link.id, form)
        return Response({'state': found['state'], 'link': _link_state(link)})


class SignView(PortalView):
    def post(self, request, token, form):
        opened = self.open(request, token, write=True)
        body = _body(request)
        form_services.sign(opened.link.id, form, body.get('name'), body.get('sign_anyway', False))
        found, link = card(opened.link.id, form)
        return Response({'questionnaire': found, 'link': _link_state(link)})
