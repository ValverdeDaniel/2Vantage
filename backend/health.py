"""GET /api/health/ — plain Django view, no auth, never cached (plan.md §3.5)."""

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import JsonResponse
from django.views.decorators.cache import never_cache

_migrations_done = False


def _pending_migrations():
    global _migrations_done
    if _migrations_done:
        return 0
    executor = MigrationExecutor(connection)
    pending = len(executor.migration_plan(executor.loader.graph.leaf_nodes()))
    _migrations_done = pending == 0
    return pending


@never_cache
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('select 1')
        pending = _pending_migrations()
    except Exception as exc:  # noqa: BLE001 — the class name is all we reveal
        return JsonResponse({'ok': False, 'database': type(exc).__name__, 'commit': settings.GIT_SHA}, status=503)
    return JsonResponse({'ok': True, 'database': 'ok', 'commit': settings.GIT_SHA, 'migrations_pending': pending})
