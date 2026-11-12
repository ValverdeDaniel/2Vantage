"""Plan template download and import (plan.md §7.7, §9.3)."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from deals import lines
from deals.downloads import file_response
from deals.models import Deal
from documents import services as documents

from . import services, template


class TemplateDownloadView(APIView):
    def get(self, request, pk):
        deal = get_object_or_404(Deal.objects.select_related('client'), pk=pk)
        line = request.query_params.get('line') or None
        if line and line not in lines.BY_KEY:
            raise ValidationError({'line': ['Unknown line.']})
        content = template.export(deal, line)
        suffix = f' - {lines.label(line)}' if line else ''
        return file_response(io.BytesIO(content), f'{deal.client.name} - Plan template{suffix}.xlsx')


class TemplateImportView(APIView):
    def post(self, request, pk):
        deal = get_object_or_404(Deal, pk=pk)
        upload = request.FILES.get('file')
        if not upload:
            raise ValidationError({'file': ['Choose the filled plan template.']})
        documents.check_upload(upload)
        content = upload.read()
        operations, errors = template.read(deal, content)
        if errors:
            return Response({'create': 0, 'update': 0, 'cells_changed': 0, 'errors': errors}, status=400)
        if request.query_params.get('dry_run') == '1':
            return Response({**template.dry_run(operations), 'errors': []})
        with transaction.atomic():  # the stored file and every change, or nothing
            stored = SimpleUploadedFile(upload.name, content)
            document = documents.upload(request.user, deal, stored, {'kind': 'other', 'label': 'Plan template import'})
            result = services.apply_template(request.user, deal, operations, document)
        return Response({**result, 'errors': []})
