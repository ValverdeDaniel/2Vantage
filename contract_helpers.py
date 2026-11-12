"""The Q.3 contracts every app passes (plan.md §12.3, docs/porting/Q-testing.md Q.3). Re-exported by conftest.py.

Each app keeps its own small tables in its tests and calls these:
1. Write path: `write_path_contract(user, obj, call, read, later)` (or `assert_write_path` alone).
2. GETs write nothing: `sweep_gets(client, apps, samples)` walks Django's URL registry at runtime.
3. Permission matrix: `check_permissions(actors, apps, matrix, samples, no_csrf)`.

`samples` maps a route, as Django spells it ("api/deals/<int:pk>/"), to its path arguments, plus optional
"query" (a dict) and "expect" (the status a GET answers, 200 by default). A route with arguments and no sample fails.
`matrix` rows are (method, route, {actor: status}) or (method, route, {actor: status}, body).
"""

import re
from datetime import timedelta
from unittest import mock

import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.urls import URLResolver, get_resolver

METHODS = ('get', 'post', 'put', 'patch', 'delete')
_PARAM = re.compile(r'<(?:\w+:)?(\w+)>')
_WRITE = re.compile(r'^\s*(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+"?(\w+)"?', re.IGNORECASE)


# ---- the URL registry ------------------------------------------------------------------------------------------


def routes(apps):
    """[(route, view)] for every URL whose view lives in one of `apps` (None: every app)."""
    found = []

    def walk(patterns, prefix):
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
                continue
            view = getattr(pattern.callback, 'view_class', None) or pattern.callback
            if apps is None or view.__module__.split('.')[0] in apps:
                found.append((prefix + str(pattern.pattern), view))

    walk(get_resolver().url_patterns, '')
    return found


def methods(view):
    if isinstance(view, type):
        return [method for method in METHODS if hasattr(view, method)]
    return ['get']


def _url(route, sample):
    kwargs = {key: value for key, value in sample.items() if key not in ('query', 'expect')}
    missing = [name for name in _PARAM.findall(route) if name not in kwargs]
    if missing:
        return None
    return '/' + _PARAM.sub(lambda match: str(kwargs[match.group(1)]), route)


def _close(response):
    """Read a streamed file to its end; the test client then closes it (a second close would end the connection)."""
    if getattr(response, 'streaming', False):
        b''.join(response.streaming_content)


# ---- 1. the write path -----------------------------------------------------------------------------------------


def _state(obj):
    return type(obj).objects.filter(pk=obj.pk).values().get()


def _log():
    from deals.models import Activity

    return {row['id']: row for row in Activity.objects.values('id', 'updated_at', 'count', 'changes', 'summary')}


def later_clock(minutes=11):
    """Patch the clock past the coalescing window, so the next write gets its own Activity row."""
    from deals import clock

    return mock.patch.object(clock, 'now', return_value=clock.now() + timedelta(minutes=minutes))


def assert_write_path(call, obj, *, keys_only=False, lock=True):
    """`call()` changes `obj`, locks its row, writes one Activity row with before and after (or keys only), and the
    same call again changes nothing: not the row (values, sources, `updated_at`) and not Activity. Returns the row."""
    from deals.models import Activity

    state, log = _state(obj), _log()
    with CaptureQueriesContext(connection) as queries:
        call()
    changed_state, changed_log = _state(obj), _log()
    assert changed_state != state, 'the call changed nothing'
    if lock:
        table = type(obj)._meta.db_table
        locks = [q['sql'] for q in queries.captured_queries if 'FOR UPDATE' in q['sql'] and f'"{table}"' in q['sql']]
        assert locks, f'the call did not lock its {table} row'
    touched = [pk for pk, row in changed_log.items() if log.get(pk) != row]
    assert len(touched) == 1, f'the call wrote {len(touched)} Activity rows, not one'
    row = Activity.objects.get(pk=touched[0])
    assert row.changes, 'the Activity row has no changes'
    for entry in row.changes:
        if keys_only:
            assert isinstance(entry['k'], list), f'{entry["t"]} kept values on a key-only row'
        else:
            assert isinstance(entry['k'], dict) and entry['k'], f'{entry["t"]} has no before and after'
            assert all(len(pair) == 2 and pair[0] != pair[1] for pair in entry['k'].values())
    call()
    assert _state(obj) == changed_state, 'the same call again changed the row'
    assert _log() == changed_log, 'the same call again touched Activity'
    return row


def _written(call):
    log = _log()
    call()
    return max(pk for pk, row in _log().items() if log.get(pk) != row)


def write_path_contract(user, obj, call, read, later, *, keys_only=False, lock=True):
    """The whole of Q.3 #1. `read(obj)` projects what Revert must restore (e.g. lambda plan: plan.values);
    `later()` writes the same key again. Revert restores once, then answers "already undone"; after a later write
    it is refused, naming the keys. A key-only row refuses Revert with a sentence."""
    from deals import activity

    def current():
        return read(type(obj).objects.get(pk=obj.pk))

    before = current()
    row = assert_write_path(call, obj, keys_only=keys_only, lock=lock)
    if keys_only:
        with pytest.raises(activity.Refused) as refused:
            activity.revert(row.id, user)
        assert refused.value.sentence == activity.KEYS_ONLY
        return row
    activity.revert(row.id, user)
    assert current() == before, 'Revert did not restore the earlier value'
    with pytest.raises(activity.Refused) as refused:
        activity.revert(row.id, user)
    assert refused.value.sentence == activity.ALREADY_UNDONE
    again = _written(call)
    with later_clock():
        later()
    with pytest.raises(activity.Refused) as refused:
        activity.revert(again, user)
    assert refused.value.keys, 'a Revert after a later write must name the keys'
    return row


# ---- 2. GETs write nothing -------------------------------------------------------------------------------------


def sweep_gets(client, apps, samples):
    """Call every GET of `apps` with its sample ids; fail on any INSERT, UPDATE or DELETE except access rows."""
    from deals.activity import ACCESS
    from deals.models import Activity

    failures = []
    for route, view in routes(apps):
        if 'get' not in methods(view):
            continue
        sample = samples.get(route, {})
        url = _url(route, sample)
        if url is None:
            failures.append(f'{route}: no sample arguments')
            continue
        log = _log()
        with CaptureQueriesContext(connection) as queries:
            response = client.get(url, sample.get('query', {}))
        _close(response)
        if response.status_code != sample.get('expect', 200):
            failures.append(f'GET {url} answered {response.status_code}')
        for query in queries.captured_queries:
            write = _WRITE.match(query['sql'])
            if write and write.group(2) != Activity._meta.db_table:
                failures.append(f'GET {url} wrote: {query["sql"][:160]}')
        touched = [pk for pk, row in _log().items() if log.get(pk) != row]
        bad = Activity.objects.filter(pk__in=touched).exclude(action__in=ACCESS)
        if bad.exists():
            failures.append(f'GET {url} recorded Activity: {", ".join(bad.values_list("action", flat=True))}')
    assert not failures, '\n'.join(failures)


# ---- 3. the permission matrix ----------------------------------------------------------------------------------


def _request(client, method, url, query, body):
    if method == 'GET':
        return client.get(url, query)
    if query:
        url += '?' + '&'.join(f'{key}={value}' for key, value in query.items())
    return getattr(client, method.lower())(url, body or {}, format='json')


def check_permissions(actors, apps, matrix, samples, no_csrf):
    """Every endpoint of `apps` has a row; each actor gets the row's status; a write without CSRF answers 403.

    `actors` maps names to signed-in (or signed-out) API clients; `no_csrf` is a signed-in client that enforces CSRF.
    Every request runs in a savepoint that is rolled back, so the rows' order does not matter.
    """
    rows = {(row[0].upper(), row[1]): (row[2], row[3] if len(row) > 3 else None) for row in matrix}
    failures = [
        f'{method.upper()} {route}: no row in the permission matrix'
        for route, view in routes(apps)
        for method in methods(view)
        if (method.upper(), route) not in rows
    ]
    for (method, route), (expect, body) in rows.items():
        sample = samples.get(route, {})
        url = _url(route, sample)
        if url is None:
            failures.append(f'{route}: no sample arguments')
            continue
        checks = [*expect.items(), *([('no_csrf', 403)] if method != 'GET' else [])]
        for actor, status in checks:
            client = no_csrf if actor == 'no_csrf' else actors[actor]
            with transaction.atomic():
                response = _request(client, method, url, sample.get('query', {}), body)
                _close(response)
                transaction.set_rollback(True)
            if response.status_code != status:
                failures.append(f'{method} {url} as {actor}: {response.status_code}, expected {status}')
    assert not failures, '\n'.join(failures)
