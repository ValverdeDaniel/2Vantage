"""The census files (plan.md §7.7, §9.1, §9.2; C38): the template and the export. A file that carries member data
writes one `downloaded` Activity row naming the kind of file, never a person (§3.8, `log_access`); a blank template
carries none and writes nothing. The names carry the client's name, never a person's (§9).
"""

import io

from rest_framework.views import APIView

from deals import activity
from deals.downloads import file_response

from . import template
from .views import _deal


class TemplateView(APIView):
    """GET deals/{id}/census/template/ — the census template, prefilled from the roster when it has people (§9.1)."""

    def get(self, request, pk):
        deal = _deal(pk)
        content, prefilled = template.template(deal)
        if prefilled:
            activity.log_access(deal, request.user, 'downloaded', 'the census template, prefilled', None, area='census')
        return file_response(io.BytesIO(content), f'{deal.client.name} - Census template.xlsx')


class ExportView(APIView):
    """GET deals/{id}/census/export/ — the full census workbook, unmasked (§9.2); every download is logged."""

    def get(self, request, pk):
        deal = _deal(pk)
        content = template.export(deal)
        activity.log_access(deal, request.user, 'downloaded', 'the census', None, area='census')
        return file_response(io.BytesIO(content), f'{deal.client.name} - Census.xlsx')
