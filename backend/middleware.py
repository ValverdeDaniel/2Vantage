from django.middleware.gzip import GZipMiddleware


class JsonGZipMiddleware(GZipMiddleware):
    """Gzip JSON responses only. File downloads are never compressed (plan.md §3.5, §3.6)."""

    def process_response(self, request, response):
        if not response.get('Content-Type', '').startswith('application/json'):
            return response
        return super().process_response(request, response)
