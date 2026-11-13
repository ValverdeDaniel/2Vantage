"""Review & requests API for the Ask card, the settings card, People & links, edit mode, their form and the sections'
boards (plan.md §7.13; L30, L34–L42, L45–L48, L72; B37; C27, C28, C30; slice 57). Thin: parse → service or selector →
answer with what the screen redraws. Ids from the path are integers: past bigint, or on another deal, 404.

- GET  deals/{id}/review/requests/ → {requests: [request row]}: People & links, every link ever made (L38).
- POST deals/{id}/review/requests/{rid}/form/[?dry_run=1] {ids?, off?, on?, security?, message?, settings?} → {request,
  changed, pins: [{link_id, name, pin}], sent, closed, activity_id}; the dry run → {asks, adds, offs, floor, level,
  owed, refused, warnings, numbers}. 400 by field; 409 {detail} or {detail, needs_level} (L42).
- POST deals/{id}/review/requests/{rid}/people/ {people} → 201 {request, links: [made], activity_id} (L72).
- POST deals/{id}/review/preview/ {request_id?, link_id?, asks?, blank?, message?, off?, on?, ids?} → {page, why,
  new_refs}: the client's page as it would be (L30), from the portal's own builder on stand-ins; writes nothing.
- POST deals/{id}/review/enter/ {answers: {ref: value}, origin: typed | relay} → {saved, activity_ids} (L35).
- GET  deals/{id}/review/census-blanks/?required=1 → the census blanks person by person, at most 500 (L35).
- GET  deals/{id}/review/section/?surface=intake | census[&column=] → that section's board (B37; C27, C30) or one
  column's people (C28). `private, no-store` (it names people).
- POST deals/{id}/review/rules/ {surface, rules} → {changed, activity_id, board}: Auto, Required or Waived (and an
  intake question's note for the client) through the owner's `set_rules` (B37, C27; OQ17).
"""

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from census import fields as census_fields
from census.services import set_rules as census_rules
from deals import clock
from intake.services import set_rules as intake_rules

from .models import ClientLink, ClientRequest
from .rules import asks as ask_rules
from .selectors import census_blanks, census_board, drafted, intake_board
from .selectors import requests as request_rows
from .services import access, form, form_preview
from .services.enter import enter as enter_answers
from .views import MAX_ID, _activity_id, _body, _deal, _made

SURFACES = ('intake', 'census')


def _request(deal, rid):
    if rid > MAX_ID or not ClientRequest.objects.filter(pk=rid, deal=deal).exists():
        raise Http404
    return rid


def _number(raw, field):
    if raw in (None, ''):
        return None
    if isinstance(raw, bool) or not str(raw).isdigit() or len(str(raw)) > 18:
        raise ValidationError({field: ['Send it as a number.']})
    return int(raw)


class FormView(APIView):
    def post(self, request, pk, rid):
        deal = _deal(pk)
        _request(deal, rid)
        data = _body(request)
        if request.query_params.get('dry_run') in ('1', 'true'):
            found = form_preview.preview(request.user, deal.id, rid, data)
            return Response(found._asdict())
        done = form.update(request.user, deal.id, rid, data)
        row = request_rows.one(rid, clock.now())
        names = {person['link_id']: person['name'] for person in row['recipients']}
        return Response({
            'request': row,
            'changed': done.changed,
            'pins': [{'link_id': lid, 'name': names.get(lid, ''), 'pin': pin} for lid, pin in done.pins.items()],
            'sent': done.sent,
            'closed': done.closed,
            'activity_id': _activity_id(done.activity),
        })  # fmt: skip


class PeopleView(APIView):
    def post(self, request, pk, rid):
        deal = _deal(pk)
        _request(deal, rid)
        made = access.add_people(request.user, deal.id, rid, _body(request).get('people'))
        answer = {
            'request': request_rows.one(rid, clock.now()),
            'links': [_made(*one) for one in made.links],
            'activity_id': _activity_id(made.activity),
        }
        return Response(answer, status=status.HTTP_201_CREATED)


def _preview_open(deal, data, rid):
    request = ClientRequest.objects.get(pk=rid)
    lid = _number(data.get('link_id'), 'link_id')
    link = ClientLink.objects.filter(pk=lid, request=request).first() if lid else None
    if lid and link is None:
        raise ValidationError({'link_id': ['That person is not on this request.']})
    asks, why = form_preview.asks_after(deal, request, data)
    blank = data.get('blank') if data.get('blank') in (True, False) else None
    before = drafted.carried(deal, request.asks, request=request, link=link)
    after = drafted.carried(deal, asks, request=request, link=link)
    page = drafted.page(deal, asks, request=request, link=link, blank=blank, message=data.get('message'))
    return page, why, sorted(after - before)


class PreviewView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        rid = _number(data.get('request_id'), 'request_id')
        if rid is not None:
            page, why, new = _preview_open(deal, data, _request(deal, rid))
            return Response({'page': page, 'why': why, 'new_refs': new})
        asks, errors = ask_rules.clean(data.get('asks'))
        errors.pop('asks', None)  # nothing picked yet is a page with nothing on it
        if errors:
            raise ValidationError(errors)
        message = str(data.get('message') or '')
        page = drafted.page(deal, asks, blank=data.get('blank') is True, message=message)
        return Response({'page': page, 'why': '', 'new_refs': sorted(drafted.carried(deal, asks))})


class EnterView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        done = enter_answers(request.user, deal.id, data.get('answers'), origin=data.get('origin') or 'relay')
        return Response({'saved': done.saved, 'activity_ids': done.activity_ids})


class CensusBlanksView(APIView):
    def get(self, request, pk):
        deal = _deal(pk)
        required = request.query_params.get('required') in ('1', 'true')
        answer = Response(census_blanks.blanks(deal, required_only=required))
        answer['Cache-Control'] = 'private, no-store'
        return answer


def _surface(raw):
    if raw not in SURFACES:
        raise ValidationError({'surface': [f'Name the section as one of: {", ".join(SURFACES)}.']})
    return raw


def _section(deal, surface):
    return intake_board.board(deal) if surface == 'intake' else census_board.board(deal)


class SectionView(APIView):
    def get(self, request, pk):
        deal = _deal(pk)
        surface = _surface(request.query_params.get('surface') or 'intake')
        column = request.query_params.get('column')
        if column:
            if surface != 'census' or column not in census_fields.BY_KEY or column in census_fields.SSN_KEYS:
                raise ValidationError({'column': ['Not a census column this board shows.']})
            answer = Response({'column': column, 'people': census_board.drill(deal, column)})
        else:
            answer = Response(_section(deal, surface))
        answer['Cache-Control'] = 'private, no-store'
        return answer


class RulesView(APIView):
    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        surface = _surface(data.get('surface'))
        write = intake_rules if surface == 'intake' else census_rules
        changed, row = write(request.user, deal.id, data.get('rules'))
        answer = Response({'changed': changed, 'activity_id': _activity_id(row), 'board': _section(deal, surface)})
        answer['Cache-Control'] = 'private, no-store'
        return answer
