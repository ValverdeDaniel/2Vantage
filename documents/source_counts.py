"""Counting what a row's `sources` say, in SQL (plan.md §3.7, §8.6; M83, M86, M87, M90, M91; O.3.1; slice 64).

The Overview's data confidence reads every value owner's `sources` (intake, census, quotes, questionnaires) at any
size in a fixed number of queries: one aggregate per owner over `jsonb_each(sources)`, and one query per owner for
the values a person marked. The owners hand in their own querysets (their live rows of the deal), so which rows count
stays each owner's rule; this module only reads the entries. Only an entry whose value is stored counts: a blank has
no value and takes no mark (O.3.1).

- `grouped(queryset)` → [Group]: the entries counted by what the review rules read (origin, file, Claude's doubt, the
  locator's state, the mark, the approval and how it was applied). `entry(group)` makes one of them back into a
  source entry, so `documents.review_rules` (`origin_bucket`, `open_warning`, …) stays the one rule: no SQL copy of it.
- `marked(queryset, cap, columns, hidden)` → [Marked]: the values marked ⚑ Needs checking or Ignored, newest first,
  at most `cap` of each, with the row's `columns` beside them. A value comes back only for keys not in `hidden` (an
  owner hides every value of member data and lasers: §3.8); a hidden key's value is never read.
Reads only.
"""

from collections import namedtuple

from django.db import connection

from .review_rules import CHECKING, IGNORED

Group = namedtuple('Group', 'origin doc low loc mark confirmed via count')
Marked = namedtuple('Marked', 'row_id key state at by doc value columns')

# A value is stored when the row's values (`values`, or `answers` on intake and the forms) hold the key with something
# in it ('' and [] are blanks).
_STORED = """jsonb_typeof(e.value) = 'object' AND {v} ? e.key
    AND jsonb_typeof({v} -> e.key) <> 'null' AND ({v} ->> e.key) NOT IN ('', '[]', '{{}}')"""
_FIELDS = """e.value ->> 'origin',
    e.value ->> 'doc',
    COALESCE(e.value ->> 'low', '') NOT IN ('', 'false', '0'),
    CASE WHEN jsonb_typeof(e.value -> 'loc') = 'object' THEN e.value -> 'loc' ->> 'state' END,
    CASE WHEN jsonb_typeof(e.value -> 'mark') = 'object' THEN e.value -> 'mark' ->> 'state' END,
    jsonb_typeof(e.value -> 'confirmed') = 'object' AND e.value -> 'confirmed' <> '{}'::jsonb,
    CASE WHEN jsonb_typeof(e.value -> 'confirmed') = 'object' THEN e.value -> 'confirmed' ->> 'via' END"""


def _column(model, name):
    return 't.' + connection.ops.quote_name(model._meta.get_field(name).column)


def _source(queryset, values):
    """(FROM … WHERE clause, params, pk, the values column) over the queryset's rows and their source entries whose
    value is stored."""
    model = queryset.model
    table = connection.ops.quote_name(model._meta.db_table)
    pk = connection.ops.quote_name(model._meta.pk.column)
    rows, params = queryset.order_by().values('pk').query.sql_with_params()
    column = _column(model, values)
    where = f't.{pk} IN ({rows}) AND {_STORED.format(v=column)}'
    source = f'{table} t CROSS JOIN LATERAL jsonb_each({_column(model, "sources")}) e WHERE {where}'
    return source, list(params), pk, column


def _doc(raw):
    return int(raw) if raw and str(raw).isdigit() else None


def grouped(queryset, values='values'):
    """[Group(origin, doc, low, loc, mark, confirmed, via, count)] over the queryset's stored values: one query.
    `values` names the row's values field (`answers` on intake and the forms)."""
    source, params, _pk, _stored = _source(queryset, values)
    sql = f'SELECT {_FIELDS}, COUNT(*) FROM {source} GROUP BY 1, 2, 3, 4, 5, 6, 7'
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        found = cursor.fetchall()
    return [
        Group(origin or '', _doc(doc), low, loc or '', mark or '', confirmed, via or '', n)
        for origin, doc, low, loc, mark, confirmed, via, n in found
    ]


def entry(group):
    """The source entry a group stands for, as the review rules read it."""
    out = {'origin': group.origin}
    if group.doc:
        out['doc'] = group.doc
    if group.low:
        out['low'] = True
    if group.loc:
        out['loc'] = {'state': group.loc}
    if group.mark:
        out['mark'] = {'state': group.mark}
    if group.confirmed:
        out['confirmed'] = {'via': group.via} if group.via else {'by': None}
    return out


def marked(queryset, cap, *, columns=(), hidden=None, values='values'):
    """[Marked(row_id, key, state, at, by, doc, value, columns)], newest first, at most `cap` per mark state, over the
    queryset's stored values marked ⚑ Needs checking or Ignored. `hidden`: None hides every value; else the keys whose
    value stays unread (each other key's value comes back as text)."""
    source, params, pk, stored = _source(queryset, values)
    names = [f'c{n}' for n in range(len(columns))]
    extra = ''.join(
        f', {_column(queryset.model, column)} AS {name}' for column, name in zip(columns, names, strict=True)
    )
    value = 'NULL' if hidden is None else f'CASE WHEN e.key = ANY(%s) THEN NULL ELSE {stored} ->> e.key END'
    state, at = "e.value -> 'mark' ->> 'state'", "e.value -> 'mark' ->> 'at'"
    sql = f"""SELECT row_id, key, state, at, marked_by, doc, value{''.join(f', {name}' for name in names)}
        FROM (SELECT t.{pk} AS row_id, e.key AS key, {state} AS state, {at} AS at,
                     e.value -> 'mark' ->> 'by' AS marked_by, e.value ->> 'doc' AS doc, {value} AS value{extra},
                     row_number() OVER (PARTITION BY {state} ORDER BY {at} DESC, t.{pk} DESC, e.key) AS place
              FROM {source} AND jsonb_typeof(e.value -> 'mark') = 'object' AND {state} IN (%s, %s)) found
        WHERE place <= %s ORDER BY at DESC, row_id DESC, key"""
    args = ([list(hidden)] if hidden is not None else []) + params + [CHECKING, IGNORED, cap]
    with connection.cursor() as cursor:
        cursor.execute(sql, args)
        found = cursor.fetchall()
    out = []
    for row_id, key, mark_state, mark_at, by, doc, text, *rest in found:
        by = int(by) if by and str(by).isdigit() else None
        out.append(Marked(row_id, key, mark_state, mark_at or '', by, _doc(doc), text, tuple(rest)))
    return out
