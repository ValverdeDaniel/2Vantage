"""The Book's records and By person (plan.md §7.10, §8.18; H49–H58, H68). Reads need a commission tier and follow it
(the own tier sees its own records and its own share, H102); every write is the all tier's. Thin: parse → service →
answer with what the screen redraws. Ids are parsed as ints (a bad one answers 400, a missing one 404).

GET  commissions/records/ ?q, client, deal, party, record, status, year → book.book (H49–H51, the tiles H45)
POST commissions/records/ {client | client_name + relationship, line, …facts} → 201 {record, activity_id} (H58)
GET  commissions/records/export/ (the Book's filters) → the Book workbook (H52)
GET  commissions/records/{id}/ → {record, history (all tier, H57)}; PATCH {facts, notes} → {record, changed,
     activity_id} (H54, H56)
PUT  commissions/records/{id}/shares/ {shares: [{party, role, pct}] | null, reason} → {record, changed, activity_id}
POST commissions/records/{id}/rebook/ → {record, changed, activity_id} (H36)
GET  commissions/people/ ?year → book.people (H68); …/people/{party id | house}/ → its records; …/people/export/
GET  commissions/clients/ ?q → [{id, name, relationship, archived}]: Add to book's search, archived clients and clients
     with no deal included (H58, H112; the all tier)
"""

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.access import HasCommissions
from deals import activity
from deals.models import Activity, AgencySettings, Client
from deals.selectors import activity_row

from . import book, exports, record_read, services, visibility
from .models import Record
from .people_views import AllTier
from .views import MAX_ID, body

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _viewer(request):
    return visibility.Viewer(request.user)


def _record(pk, viewer):
    """The record the viewer may see, or 404."""
    if pk > MAX_ID:
        raise Http404
    records = visibility.scoped(Record.objects.select_related('client', 'booked_by', 'updated_by'), viewer)
    return get_object_or_404(records, pk=pk)


def _one(record, viewer):
    return record_read.payloads([record], viewer)[0]


def _history(record):
    rows = (
        Activity.objects.filter(changes__contains=[{'t': f'record:{record.id}'}])
        .exclude(action__in=activity.ACCESS)
        .select_related('actor', 'reverted_by')
        .order_by('-id')[:50]
    )
    out = []
    for row in rows:
        mine = [entry['k'] for entry in row.changes if entry['t'] == f'record:{record.id}']
        out.append({**activity_row(row), 'changes': mine[0] if mine else {}})
    return out


def _xlsx(content, name):
    response = HttpResponse(content, content_type=XLSX)
    response['Content-Disposition'] = f'attachment; filename="{name}"'
    return response


class ATierOrAll:
    """GET for a commission tier; any write for the all tier."""

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), HasCommissions()]
        return [IsAuthenticated(), AllTier()]


class RecordsView(ATierOrAll, APIView):
    def get(self, request):
        return Response(book.book(request.query_params, _viewer(request)))

    def post(self, request):
        written = services.add_to_book(request.user, body(request))
        record = Record.objects.select_related('client', 'booked_by', 'updated_by').get(pk=written.record.pk)
        answer = {'record': _one(record, _viewer(request)), 'activity_id': written.activity.id}
        return Response(answer, status=201)


class RecordsExportView(APIView):
    permission_classes = [IsAuthenticated, HasCommissions]

    def get(self, request):
        answer = book.book(request.query_params, _viewer(request))
        content = exports.book(answer, AgencySettings.get().name)
        return _xlsx(content, 'commission-book.xlsx')


class RecordView(ATierOrAll, APIView):
    def get(self, request, pk):
        viewer = _viewer(request)
        record = _record(pk, viewer)
        return Response({'record': _one(record, viewer), 'history': _history(record) if viewer.all else []})

    def patch(self, request, pk):
        viewer = _viewer(request)
        _record(pk, viewer)
        written = services.edit_record(request.user, pk, body(request))
        record = _record(pk, viewer)
        activity_id = written.activity.id if written.activity else None
        return Response({'record': _one(record, viewer), 'changed': written.changed, 'activity_id': activity_id})


class RecordSharesView(APIView):
    permission_classes = [IsAuthenticated, AllTier]

    def put(self, request, pk):
        viewer = _viewer(request)
        _record(pk, viewer)
        data = body(request)
        written = services.set_shares(request.user, pk, data.get('shares'), data.get('reason'))
        activity_id = written.activity.id if written.activity else None
        record = _one(_record(pk, viewer), viewer)
        return Response({'record': record, 'changed': written.changed, 'activity_id': activity_id})


class RecordRebookView(APIView):
    permission_classes = [IsAuthenticated, AllTier]

    def post(self, request, pk):
        viewer = _viewer(request)
        record = _record(pk, viewer)
        written = services.rebook_record(request.user, record.id)
        activity_id = written.activity.id if written.activity else None
        changed = [entry['t'] for entry in written.changes]
        return Response({'record': _one(_record(pk, viewer), viewer), 'changed': changed, 'activity_id': activity_id})


class PeopleView(APIView):
    permission_classes = [IsAuthenticated, HasCommissions]

    def get(self, request):
        return Response(book.people(request.query_params, _viewer(request)))


class PersonView(APIView):
    permission_classes = [IsAuthenticated, HasCommissions]

    def get(self, request, key):
        if key != book.HOUSE and (not key.isdigit() or int(key) > MAX_ID):
            raise Http404
        return Response(book.person_records(key, request.query_params, _viewer(request)))


class PeopleExportView(APIView):
    permission_classes = [IsAuthenticated, HasCommissions]

    def get(self, request):
        viewer = _viewer(request)
        people = book.people(request.query_params, viewer)

        def records_of(key):
            return book.person_records(str(key), request.query_params, viewer)['rows']

        content = exports.by_person(people, records_of, AgencySettings.get().name)
        return _xlsx(content, 'commission-by-person.xlsx')


class ClientPickView(APIView):
    """Add to book searches the existing clients first (H58): every client by name, archived ones and clients with no
    deal among them (H112), at most 20."""

    permission_classes = [IsAuthenticated, AllTier]

    def get(self, request):
        q = ' '.join(str(request.query_params.get('q') or '').split())[:100]
        clients = Client.objects.filter(name__icontains=q) if q else Client.objects.none()
        rows = clients.order_by('name', 'id').values('id', 'name', 'relationship', 'archived_at')[:20]
        return Response(
            [{'id': r['id'], 'name': r['name'], 'relationship': r['relationship'], 'archived': bool(r['archived_at'])}
             for r in rows]
        )  # fmt: skip
