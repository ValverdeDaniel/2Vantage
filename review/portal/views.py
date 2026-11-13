"""The client portal's API (plan.md §7.14; L.6 endpoints; rule 11): `/api/portal/<token>/…`, public.

Every view: AllowAny, no authentication classes (a staff session is read by the guard alone), throttled per link
(throttles.py), and every answer, refusals included, carries `Cache-Control: private, no-store`, `Referrer-Policy:
no-referrer` and `X-Robots-Tag: noindex`, plus a fresh `X-Link-Verification` once a PIN was proved.
- GET  portal/{t}/ → the page (payload.KEYS); the client's GET records the open (the one write a GET makes).
- POST portal/{t}/verify/ {pin} → {verified: true} with the token header; 400 {detail, tries_left, locked}.
- POST portal/{t}/save/ {answers: {ref: {value, base}}} → {saved: [ref], bases: {ref: base}, link: {expires_at,
  days_left}, activity_id}; 400 {answers: {ref: sentence}}; 409 {detail, conflicts: [{ref, theirs, base}]}.
- POST portal/{t}/submit/ {answers} → the save's answer plus {submitted_at}.
- POST portal/{t}/files/ multipart {slot, file} → 201 {slot, received: [{name, at}], link}.
- POST portal/{t}/people/ {people: [{kind, first_name, last_name, employee_id?, relationship?, dob?}]} → 201
  {people: [person], add_people}.
- POST portal/{t}/sign/ {name} → {bor: {signed, name, signed_at, on_file}, link}.
- POST portal/{t}/questions/ {questions: [{ref, text}]} → 201 {follow_ups} (slice 56); 400 {questions: [sentence]}.
- POST portal/{t}/seen/ → {seen_at}: the page's last look at its follow-ups (slice 56).
- GET  portal/{t}/stamp/ → {form_stamp, days_left} (the poll; writes nothing).
- GET  portal/{t}/census-template/ → the blank census template (B3).
- GET  portal/moved/ → {agency} for the "This link has moved" page (L136); it takes no token.
404 bad token, 410 gone (with the agency), 428 PIN needed, 403 a staff session's write (guard.py).
"""

import io

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from census.template import template
from deals import clock
from deals.downloads import file_response

from ..models import ClientLink
from ..rules import policy
from ..rules import portal as portal_rules
from ..services import answers as answer_services
from ..services import client_adds, pins, questions, stamps
from . import census_part, files_part, follow_ups, guard, payload, throttles
from .asked import asked

HEADERS = {'Cache-Control': 'private, no-store', 'Referrer-Policy': 'no-referrer', 'X-Robots-Tag': 'noindex'}
WRONG_PIN = 'That PIN did not work. {left} more {tries} before this link locks.'


class PortalView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (throttles.Write,)
    verification = ''

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        for name, value in HEADERS.items():
            response[name] = value
        if self.verification:
            response[guard.HEADER] = self.verification
        return response

    def open(self, request, token, *, write=False):
        opened = guard.open_link(request, token, write=write)
        self.verification = opened.verification
        return opened


def _body(request):
    if not isinstance(request.data, dict):
        raise ValidationError({'non_field_errors': ['Send the fields as an object.']})
    return request.data


def _link_state(link):
    return {'expires_at': link.expires_at.isoformat(), 'days_left': policy.days_left(link.expires_at, clock.now())}


class PageView(PortalView):
    throttle_classes = (throttles.Read,)

    def get(self, request, token):
        opened = self.open(request, token)
        if opened.staff is None:
            stamps.record_open(opened.link.id)
        return Response(payload.build(opened.link, opened.request, opened.deal, staff=opened.staff is not None))


class VerifyView(PortalView):
    throttle_classes = (throttles.Pin,)

    def post(self, request, token):
        link = guard.find(token)
        if guard.staff_user(request) is not None:
            raise guard.StaffWrite()  # a staff session never needs the PIN, and proves nothing for the client
        if not policy.opens(link, clock.now(), closed=link.request.closed_at is not None):
            raise guard.Gone()
        checked = pins.check(link.id, _body(request).get('pin'))
        if checked.outcome == pins.OK:
            link.refresh_from_db(fields=['pin_version'])
            self.verification = guard.issue(link)
            return Response({'verified': True})
        if checked.outcome == pins.NONE:
            return Response({'verified': True})
        locked = checked.outcome == pins.LOCKED
        left = checked.tries_left
        detail = guard.LOCKED if locked else WRONG_PIN.format(left=left, tries='try' if left == 1 else 'tries')
        return Response({'detail': detail, 'tries_left': left, 'locked': locked}, status=status.HTTP_400_BAD_REQUEST)


def _saved_answer(done):
    return {
        'saved': done.saved,
        'bases': done.bases,
        'link': _link_state(done.link),
        'activity_id': done.activity.id if done.activity else None,
    }


class SaveView(PortalView):
    def post(self, request, token):
        opened = self.open(request, token, write=True)
        done = answer_services.save(opened.link.id, _body(request).get('answers'))
        return Response(_saved_answer(done))


class SubmitView(PortalView):
    def post(self, request, token):
        opened = self.open(request, token, write=True)
        done = answer_services.submit(opened.link.id, _body(request).get('answers') or {})
        return Response({**_saved_answer(done), 'submitted_at': done.link.submitted_at.isoformat()})


class FilesView(PortalView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def post(self, request, token):
        opened = self.open(request, token, write=True)
        slot = str(request.data.get('slot') or '')
        files = request.FILES.getlist('file')
        if len(files) > 1:
            raise ValidationError({'file': ['Send one file at a time.']})
        client_adds.upload(opened.link.id, slot, files[0] if files else None)
        link = ClientLink.objects.get(pk=opened.link.id)
        siblings = list(opened.request.links.values_list('id', flat=True))
        got = files_part.received(files_part.shown_links(link, siblings), [slot])[slot]
        return Response({'slot': slot, 'received': got, 'link': _link_state(link)}, status=status.HTTP_201_CREATED)


class PeopleView(PortalView):
    def post(self, request, token):
        opened = self.open(request, token, write=True)
        made = client_adds.add_people(opened.link.id, _body(request).get('people'))
        link = ClientLink.objects.get(pk=opened.link.id)
        siblings = list(opened.request.links.values_list('id', flat=True))
        found = asked(link, opened.request, opened.deal, link_ids=siblings)
        ids = {member.id for member in made}
        people = [person for person in census_part.people(found, link) if person['id'] in ids]
        answer = {'people': people, 'add_people': census_part.add_people(found, siblings)}
        return Response(answer, status=status.HTTP_201_CREATED)


class SignView(PortalView):
    def post(self, request, token):
        opened = self.open(request, token, write=True)
        agent = request.headers.get('User-Agent', '')
        answer_services.sign_bor(opened.link.id, _body(request).get('name'), request.META.get('REMOTE_ADDR'), agent)
        link = ClientLink.objects.get(pk=opened.link.id)
        found = asked(link, opened.request, opened.deal, link_ids=[link.id])
        from .intake_part import section

        bor = (section(found, opened.deal, link) or {}).get('blocks', {}).get('bor')
        return Response({'bor': bor, 'link': _link_state(link)})


class QuestionsView(PortalView):
    def post(self, request, token):
        opened = self.open(request, token, write=True)
        questions.ask(opened.link.id, _body(request).get('questions'))
        link = ClientLink.objects.get(pk=opened.link.id)
        siblings = list(opened.request.links.values_list('id', flat=True))
        found = asked(link, opened.request, opened.deal, link_ids=siblings)
        cards = follow_ups.cards(
            link, opened.request, opened.deal, found, link_ids=files_part.shown_links(link, siblings)
        )
        return Response({'follow_ups': cards}, status=status.HTTP_201_CREATED)


class SeenView(PortalView):
    throttle_classes = (throttles.Poll,)

    def post(self, request, token):
        opened = self.open(request, token, write=True)
        return Response({'seen_at': questions.seen_now(opened.link.id).isoformat()})


class StampView(PortalView):
    throttle_classes = (throttles.Poll,)

    def get(self, request, token):
        opened = self.open(request, token)
        now = clock.now()
        notes = follow_ups.stamp(opened.link, opened.request)
        stamp = portal_rules.form_stamp(opened.link, opened.request, now, notes)
        return Response({'form_stamp': stamp, 'days_left': policy.days_left(opened.link.expires_at, now)})


class TemplateView(PortalView):
    throttle_classes = (throttles.Read,)

    def get(self, request, token):
        opened = self.open(request, token)
        found = asked(opened.link, opened.request, opened.deal, link_ids=[opened.link.id])
        if not (found.census_file or found.add_people):
            raise guard.Unknown()
        content, _people = template(opened.deal, blank=True)
        return file_response(io.BytesIO(content), f'{opened.deal.client.name} - Census template.xlsx')


class MovedView(PortalView):
    throttle_classes = (throttles.Read,)

    def get(self, request):
        return Response({'agency': guard.agency()})


class PreviewView(APIView):
    """GET links/{lid}/preview/ — View as client (L78), for staff: the page the link opens, read-only, no open."""

    def get(self, request, lid):
        if lid > 2**63 - 1:
            raise guard.Unknown()
        link = get_object_or_404(ClientLink.objects.select_related('request__deal__client'), pk=lid)
        built = payload.build(link, link.request, link.request.deal, staff=True, preview=True)
        return Response(built)
