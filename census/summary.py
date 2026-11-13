"""The census's facts for Agenda and the Overview (plan.md §5.10, O.2; I49–I51, C23): `facts(deal_ids) -> {deal_id:
dict}`, counts and ids only, from the stored counts (`CensusFacts`, never a census query per person; O.3.7), the
open import and the census files, in three queries however many deals are asked. Agenda (slice 60) is the first reader.

Per deal: `employees`, `dependents`, `errors`, `warnings`, `missing_required` and `readiness_pct` (the stored counts and
`facts.readiness`, the shell's Census meter and badge, slice 61; a deal with no census reads zeros, its meter 100);
`proposed_import`: the newest import waiting for its mapping to be reviewed and applied (a person's, or one a
Claude read staged, slices 51 and 59), else None; `files`: the live census files on the deal, less one marked the wrong
file.
"""

from deals.models import Deal
from documents.models import Document

from . import facts as stored_counts
from .models import CensusFacts, CensusImport


def facts(deal_ids):
    ids = list(Deal.objects.filter(pk__in=list(deal_ids)).values_list('id', flat=True))
    out = {
        deal_id: {
            'employees': 0,
            'dependents': 0,
            'errors': 0,
            'warnings': 0,
            'missing_required': 0,
            'readiness_pct': 100,
            'proposed_import': None,
            'files': 0,
        }
        for deal_id in ids
    }
    stored = CensusFacts.objects.filter(deal_id__in=ids).values(
        'deal_id', 'employees', 'dependents', 'errors', 'warnings', 'required_total', 'required_filled'
    )
    for row in stored:
        found = out[row['deal_id']]
        found.update(employees=row['employees'], dependents=row['dependents'], errors=row['errors'])
        found.update(warnings=row['warnings'], readiness_pct=stored_counts.readiness(row))
        found['missing_required'] = row['required_total'] - row['required_filled']
    proposed = (
        CensusImport.objects.filter(deal_id__in=ids, status=CensusImport.PROPOSED)
        .order_by('deal_id', '-created_at', '-id')
        .values_list('deal_id', 'id')
    )
    for deal_id, import_id in proposed:
        out[deal_id]['proposed_import'] = out[deal_id]['proposed_import'] or import_id
    files = Document.objects.filter(deal_id__in=ids, kind='census', protected=False).exclude(review_state='wrong')
    for deal_id in files.values_list('deal_id', flat=True):
        out[deal_id]['files'] += 1
    return out
