"""Advisor API: plans, line counts, the comparison, enrollment and packages (plan.md §7.8). Thin: parse → service or
selector → respond. Marks are in `mark_views.py`, roles, links, order and slots in `arrange_views.py`, moving and
removing plans in `move_views.py`."""

import io

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import activity, lines
from deals.downloads import file_response
from deals.models import Deal

from . import board_export, parse, selectors, services
from .models import Package, Plan


def _package(package):
    return {'id': package.id, 'name': package.name, 'plan_ids': sorted(p.id for p in package.plans.all())}


class LinesView(APIView):
    def get(self, request, pk):
        return Response(selectors.lines_summary(get_object_or_404(Deal, pk=pk)))


class PlansView(APIView):
    def get(self, request, pk):
        return Response(selectors.comparison(get_object_or_404(Deal, pk=pk), parse.line(request)))

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
            renews_id=parse.optional_id(data.get('renews_id'), 'renews_id'),
            replaces_ids=parse.plan_ids(data.get('replaces_ids') or [], 'replaces_ids'),
            values=data.get('values') or {},
        )
        return Response(selectors.plan_payload(plan), status=status.HTTP_201_CREATED)


class PlanView(APIView):
    def patch(self, request, plan_id):
        """Only carrier, name, plan_number, client_name, notes and values, with `expect` (F71)."""
        get_object_or_404(Plan, pk=plan_id)
        changes = {key: value for key, value in request.data.items() if key in services.plans.PATCHABLE}
        plan, _ = services.update_plan(request.user, plan_id, changes)
        return Response({**selectors.plan_payload(plan), 'activity_id': plan.activity_id})


class RenewalView(APIView):
    def post(self, request, plan_id):
        get_object_or_404(Plan, pk=plan_id)
        plan = services.create_renewal(request.user, plan_id)
        return Response(selectors.plan_payload(plan), status=status.HTTP_201_CREATED)


class CopyView(APIView):
    def post(self, request, plan_id):
        """{name?}: Duplicate, keeping the rates (F81); unnamed, the copy is "<name> — copy"."""
        get_object_or_404(Plan, pk=plan_id)
        plan = services.copy_plan(request.user, plan_id, request.data.get('name') or '')
        return Response(selectors.plan_payload(plan), status=status.HTTP_201_CREATED)


class EnrollmentView(APIView):
    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        plans = services.set_enrollment(request.user, deal, request.data.get('plans', []))
        activity_id = plans[0].activity_id if plans else None
        return Response({'plans': selectors.payloads(plans), 'activity_id': activity_id})


class PackagesView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        packages = Package.objects.filter(deal=deal, line=parse.line(request)).prefetch_related('plans')
        return Response([_package(package) for package in packages])

    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        data = request.data
        package = services.create_package(
            request.user, deal, parse.line(request), data.get('name'), data.get('plan_ids')
        )
        return Response(_package(package), status=status.HTTP_201_CREATED)


class BoardExportView(APIView):
    def get(self, request, pk):
        """⤓ Export (F93, J167): `?line=&plans=<ids in the order drawn>&columns=<keys>&orientation=rows|cols` → the
        board as Excel. Unknown plans and columns are dropped; a file that prints `sl_lasers` is a logged download."""
        deal = get_object_or_404(Deal.objects.select_related('client'), pk=pk)
        line = parse.line(request)
        raw_ids = [part for part in (request.query_params.get('plans') or '').split(',') if part.strip()]
        plan_ids = [parse.plan_id(part.strip(), 'plans') for part in raw_ids]
        keys = [part.strip() for part in (request.query_params.get('columns') or '').split(',') if part.strip()]
        transposed = request.query_params.get('orientation') == 'cols'
        content, printed = board_export.export(deal, line, plan_ids, keys, transposed)
        if 'sl_lasers' in printed:  # claimant data on an internal file (§4.3, J98)
            activity.log_access(deal, request.user, 'downloaded', 'the quote board with lasers', None, area='quotes')
        name = f'{deal.client.name} - {lines.label(line)} quote comparison.xlsx'
        return file_response(io.BytesIO(content), name)


class PackageView(APIView):
    def patch(self, request, package_id):
        get_object_or_404(Package, pk=package_id)
        return Response(_package(services.update_package(request.user, package_id, request.data)))

    def delete(self, request, package_id):
        get_object_or_404(Package, pk=package_id)
        services.delete_package(request.user, package_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
