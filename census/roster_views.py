"""The roster grid's API (plan.md §7.7; C4–C8, C24): people added, edited and removed by hand, clearing the roster,
review marks, the roster's required blanks, and one cell's source for the Documents station (E43; slice 65). Thin:
parse → service or selector → respond. Ids from paths and bodies are whole numbers (a bigger one is no row: 404); a
refusal is a 409 with a sentence that never names a value.
"""

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals.models import Deal

from . import facts, fields, selectors, services
from .models import Member
from .selectors.roster import cell_review, review_counts
from .selectors.source import value_source
from .views import MAX_ID, _body, _deal


def _member(member_id):
    if member_id > MAX_ID:
        raise Http404
    return get_object_or_404(Member.objects, pk=member_id)


def _flag(data, name):
    value = data.get(name, False)
    if not isinstance(value, bool):
        raise ValidationError({name: ['Send true or false.']})
    return value


def _origin(data):
    return 'relay' if _flag(data, 'relay') else 'typed'


class MembersView(APIView):
    """POST deals/{id}/census/members/ {kind, employee_id?, values?, relay?} → 201 {member, summary, review,
    activity_id}: ＋ Add employee, or ＋ Dep under an employee (C7)."""

    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        member, row = services.add_member(
            request.user,
            pk,
            data.get('kind'),
            employee_id=data.get('employee_id'),
            values=data.get('values') or None,
            origin=_origin(data),
        )
        answer = selectors.member_answer(deal, member.id)
        return Response({**answer, 'activity_id': row.id}, status=status.HTTP_201_CREATED)


class MemberView(APIView):
    """PATCH census/members/{id}/ {values: {key: raw}, expect?: {key: value seen}, relay?: bool} → {member, changed,
    summary, review, activity_id}: the changed person and their issues only (C6); 409 {detail, keys} when an expected
    cell changed since (O.6 #33). DELETE → 204: a soft removal, an employee's dependents too (C7, O.6 #13)."""

    def patch(self, request, member_id):
        person = _member(member_id)
        data = _body(request)
        edited = services.edit_values(
            request.user, member_id, data.get('values'), expect=data.get('expect'), origin=_origin(data)
        )
        answer = selectors.member_answer(Deal.objects.get(pk=person.deal_id), member_id)
        return Response(
            {**answer, 'changed': edited.changed, 'activity_id': edited.activity.id if edited.activity else None}
        )

    def delete(self, request, member_id):
        _member(member_id)
        services.remove_member(request.user, member_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClearView(APIView):
    """POST deals/{id}/census/clear/ {confirm: true} → 204: everyone on the roster removed, softly (§7.7)."""

    def post(self, request, pk):
        _deal(pk)
        services.clear_roster(request.user, pk, confirm=_body(request).get('confirm'))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarksView(APIView):
    """POST deals/{id}/census/marks/ {action: approve|ignore|check|clear, refs?: ["census:<member id>:<key>"]} (C8,
    E86): refs name exactly those cells; none takes every open warning on the roster (for clear, every mark). Answers
    {action, changed, activity_id, cells: [{ref, review}], review: {open, check, unflagged}}."""

    def post(self, request, pk):
        deal = _deal(pk)
        data = _body(request)
        marked = services.mark_values(request.user, pk, data.get('action'), refs=data.get('refs'))
        people = {person.id: person for person in Member.objects.filter(pk__in={m for m, _k in marked.cells})}
        return Response(
            {
                'action': marked.action,
                'changed': len(marked.cells),
                'activity_id': marked.row.id if marked.row else None,
                'cells': [
                    {
                        'ref': f'census:{member_id}:{key}',
                        'review': cell_review(people[member_id].sources.get(key)),
                    }
                    for member_id, key in marked.cells
                ],
                'review': review_counts(facts.people(deal.id)),
            }
        )


class MissingView(APIView):
    """GET deals/{id}/census/missing/ → {refs: ["census:<member id>:<key>"], count}: every required blank on the
    roster, whatever page is shown (C24; ☑ Select cells' "Select all missing")."""

    def get(self, request, pk):
        refs = selectors.missing_refs(_deal(pk))
        return Response({'refs': refs, 'count': len(refs)})


class MemberSourceView(APIView):
    """GET census/members/{id}/source/?key= → {member_id, key, label, value, hint, what, source}: where one cell was
    read, so ↗ and the Documents station open it at its own cell of the census file (E18, E43; slice 65). Read only."""

    def get(self, request, member_id):
        person = _member(member_id)
        key = request.query_params.get('key') or ''
        if key not in fields.BY_KEY:
            raise ValidationError({'key': ['Give a census column.']})
        return Response(value_source(person, key))
