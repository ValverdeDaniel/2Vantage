"""Advisor API (plan.md §7.7). Thin: parse → service or selector → respond."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import lines
from deals.models import Deal
from deals.selectors import deal_header

from . import marks, selectors, services
from .models import Package, Plan


def _line(request, required=True):
    line = request.query_params.get('line') or request.data.get('line')
    if required and line not in lines.BY_KEY:
        raise ValidationError({'line': ['Give a line of coverage.']})
    return line


def _plan_response(plan, code=status.HTTP_200_OK):
    plan = Plan.objects.prefetch_related('replaces').get(pk=plan.pk)
    return Response(selectors.plan_payload(plan), status=code)


class LinesView(APIView):
    def get(self, request, pk):
        return Response(selectors.lines_summary(get_object_or_404(Deal, pk=pk)))


class PlansView(APIView):
    def get(self, request, pk):
        return Response(selectors.comparison(get_object_or_404(Deal, pk=pk), _line(request)))

    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        data = request.data
        plan = services.create_plan(
            request.user,
            deal,
            line=data.get('line'),
            role=data.get('role'),
            carrier=data.get('carrier'),
            name=data.get('name'),
            plan_number=data.get('plan_number', ''),
            renews_id=data.get('renews_id'),
            replaces_ids=data.get('replaces_ids') or [],
            values=data.get('values') or {},
        )
        return _plan_response(plan, status.HTTP_201_CREATED)


class PlanView(APIView):
    def patch(self, request, plan_id):
        get_object_or_404(Plan, pk=plan_id)
        allowed = {'carrier', 'name', 'plan_number', 'role', 'renews_id', 'replaces_ids', 'starred', 'notes', 'values'}
        plan, _ = services.update_plan(request.user, plan_id, {k: v for k, v in request.data.items() if k in allowed})
        return _plan_response(plan)

    def delete(self, request, plan_id):
        get_object_or_404(Plan, pk=plan_id)
        services.delete_plan(request.user, plan_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RenewalView(APIView):
    def post(self, request, plan_id):
        get_object_or_404(Plan, pk=plan_id)
        return _plan_response(services.create_renewal(request.user, plan_id), status.HTTP_201_CREATED)


class CopyView(APIView):
    def post(self, request, plan_id):
        get_object_or_404(Plan, pk=plan_id)
        return _plan_response(services.copy_as_alternate(request.user, plan_id), status.HTTP_201_CREATED)


class SoldView(APIView):
    def post(self, request, plan_id):
        get_object_or_404(Plan, pk=plan_id)
        plan, deal = marks.set_sold(request.user, plan_id, bool(request.data.get('sold')))
        return Response({'plan': selectors.plan_payload(plan), 'deal': deal_header(deal)})


class RecommendView(APIView):
    def post(self, request, plan_id):
        get_object_or_404(Plan, pk=plan_id)
        return _plan_response(marks.set_recommended(request.user, plan_id, bool(request.data.get('recommended'))))


class StarView(APIView):
    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        ids = [int(i) for i in request.data.get('plan_ids', [])]
        return Response({'updated': marks.star(request.user, deal, ids, bool(request.data.get('starred')))})


class EnrollmentView(APIView):
    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        plans = marks.set_enrollment(request.user, deal, request.data.get('plans', []))
        return Response({'plans': [selectors.plan_payload(p) for p in plans]})


class OrderView(APIView):
    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        services.order(request.user, deal, _line(request), request.data.get('role'), request.data.get('plan_ids', []))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PackagesView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        line = _line(request)
        return Response([{'id': i, 'name': n, 'plan_ids': ids} for i, n, ids in selectors.member_packages(deal, line)])

    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        data = request.data
        package = marks.create_package(request.user, deal, _line(request), data.get('name'), data.get('plan_ids', []))
        return Response(
            {'id': package.id, 'name': package.name, 'plan_ids': [p.id for p in package.plans.all()]},
            status=status.HTTP_201_CREATED,
        )


class PackageView(APIView):
    def patch(self, request, package_id):
        get_object_or_404(Package, pk=package_id)
        package = marks.update_package(request.user, package_id, request.data)
        return Response({'id': package.id, 'name': package.name, 'plan_ids': [p.id for p in package.plans.all()]})

    def delete(self, request, package_id):
        get_object_or_404(Package, pk=package_id)
        marks.delete_package(request.user, package_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
