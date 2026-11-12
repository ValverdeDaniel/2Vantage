"""A census read's change set: a pointer to the import it staged (plan.md §10.5; C19, D29, D74, D110; slice 51).

Census reads always wait in the census's own review (O.3.3): the people Claude read wait on a proposed `CensusImport`
(services.reads), which the Census tab shows in its mapping dialog, dry run and Apply, and the job's change set only
points at it ("Census and intake jobs hold only a pointer", D.6): one item, op `census_import`, with counts. Nothing
in it names a person or carries a value, so the drawer's card, the strip, the job's steps and its log never do
(§10.8). The findings say what the read did in counts: people read twice, dependents placed by order, columns the
mapping assist proposed.
"""

from ..models import CensusImport
from . import staged

KEPT = ('failed_parts', 'left_out_pages', 'model', 'cost_usd', 'estimate_usd', 'partial', 'halted')


def _plural(count, one, many):
    return f'{count} {one if count == 1 else many}'


def _findings(merged, read, local, staged_twice):
    found = [dict(finding) for finding in (local or {}).get('findings') or []]
    if merged.get('duplicates'):
        found.append(
            {
                'text': f'{_plural(merged["duplicates"], "person was", "people were")} printed twice and kept once.',
                'hard': False,
            }
        )
    if merged.get('guessed'):
        found.append(
            {
                'text': f'{_plural(merged["guessed"], "dependent was", "dependents were")} placed under the '
                'employee printed above, since the page names no employee for them.',
                'hard': False,
            }
        )
    unsure = sum(len(person['low']) for person in (read or {}).get('people') or [])
    if unsure:
        found.append(
            {
                'text': f'Claude was not sure of {_plural(unsure, "value", "values")}: each is flagged to '
                'check on the roster.',
                'hard': False,
            }
        )
    if (local or {}).get('assisted'):
        found.append(
            {
                'text': f'Claude proposed {_plural(local["assisted"], "column", "columns")} from the column '
                'shapes alone (never a value): check them in the mapping dialog.',
                'hard': False,
            }
        )
    if staged_twice:
        found.append({'text': 'More than one census file was read: the last one waits for review.', 'hard': False})
    return found


def build_changes(deal, user, merged, files, extra):
    """The change set (D.6's shape) of a census read, after staging its import."""
    from ..services.reads import stage_read

    local = extra.get('local') or {}
    imports = list(local.get('imports') or [])
    read = None
    if merged.get('people'):
        first = merged['people'][0]['doc']
        imp = stage_read(user, deal.id, extra.get('job'), first, merged)
        imports.append(imp.id)
        read = imp.read
    imp = CensusImport.objects.filter(pk=imports[-1]).first() if imports else None
    documents = sorted({file.id for file in files} | ({imp.document_id} if imp and imp.document_id else set()))
    out = {key: extra[key] for key in KEPT if key in extra}
    out.update(v=1, target='census', documents=documents, findings=_findings(merged, read, local, len(imports) > 1))
    if imp is None:
        out.update(summary='No one was found to read in these files.', counts={}, items=[])
        return out
    counted = staged.counts(imp.read) if read is not None else {'people': 0, 'employees': 0, 'dependents': 0}
    mapped = sum(1 for item in imp.mapping if item['field'])
    if read is not None:
        people = _plural(counted['people'], 'person', 'people')
        employees = _plural(counted['employees'], 'employee', 'employees')
        dependents = _plural(counted['dependents'], 'dependent', 'dependents')
        summary = f'Read {people} ({employees}, {dependents}): waiting on the Census tab'
    else:
        summary = f'Mapped {mapped} of {len(imp.mapping)} census columns: waiting on the Census tab'
    item = {
        'id': 'import',
        'op': 'census_import',
        'import': imp.id,
        'tick': True,
        'read': read is not None,
        'columns': mapped,
        'assisted': local.get('assisted', 0),
        **counted,
    }
    out.update(summary=summary, counts={**counted, 'columns': mapped}, items=[item])
    return out
