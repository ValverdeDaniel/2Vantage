"""The census's facts for Agenda and the Overview (plan.md §5.10; I49–I51): the stored counts, the import waiting for
its mapping and the census files, for many deals at once in the same queries (Q.3 #4). Synthetic files only."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from census import summary
from conftest import make_deal

from .helpers import family, import_file, imported, roster, upload, xlsx

pytestmark = pytest.mark.django_db

SMITH = family('E1', 'Smith', deps=[('Spouse', 'Jordan', '02/02/1981')])


def test_I49_I51_facts_say_whether_a_census_is_in_waiting_for_its_mapping_or_only_on_file(user, deal):
    mapped = make_deal(user, name='Mapped Co.')
    filed = make_deal(user, name='Filed Co.')
    imported(user, deal, xlsx(roster(SMITH)))
    waiting = import_file(user, mapped, xlsx(roster(SMITH)))
    upload(user, filed, xlsx(roster(SMITH)))
    found = summary.facts([deal.id, mapped.id, filed.id, 10**9])
    assert set(found) == {deal.id, mapped.id, filed.id}
    assert (found[deal.id]['employees'], found[deal.id]['dependents']) == (1, 1)
    assert found[deal.id]['proposed_import'] is None
    assert found[mapped.id]['proposed_import'] == waiting.id and found[mapped.id]['employees'] == 0
    assert found[filed.id] == {
        'employees': 0,
        'dependents': 0,
        'errors': 0,
        'warnings': 0,
        'missing_required': 0,
        'readiness_pct': 100,
        'proposed_import': None,
        'files': 1,
    }


def test_Q3_4_census_facts_read_in_the_same_queries_for_one_deal_or_many(user):
    deals = [make_deal(user, name=f'Co {n}') for n in range(4)]
    for deal in deals:
        import_file(user, deal, xlsx(roster(SMITH)))

    def queries(ids):
        with CaptureQueriesContext(connection) as found:
            summary.facts(ids)
        return len(found.captured_queries)

    assert queries([deals[0].id]) == queries([deal.id for deal in deals])
