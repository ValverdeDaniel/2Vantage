"""manage.py seed_golden: builds every spec through the services and replaces what an earlier run built (§12.6)."""

import io

import pytest
from django.core.management import CommandError, call_command

from deals.models import Client, Deal

pytestmark = pytest.mark.django_db


def _seed(*keys):
    out = io.StringIO()
    call_command('seed_golden', *keys, stdout=out)
    return out.getvalue()


def test_PAR1_seed_golden_is_idempotent():
    first = _seed()
    names = [line.split(': deal')[0].split(' ', 1)[1] for line in first.splitlines()]
    assert names
    before = {name: Deal.objects.get(client__name=name).id for name in names}
    _seed()
    for name in names:
        assert Client.objects.filter(name=name).count() == 1, name
        assert Deal.objects.get(client__name=name).id != before[name], name  # replaced, not added beside


def test_PAR1_seed_golden_builds_only_the_named_deal():
    out = _seed('gd2')
    assert out.startswith('GD2 ') and len(out.splitlines()) == 1


def test_PAR1_seed_golden_refuses_an_unknown_deal():
    with pytest.raises(CommandError, match='No golden spec named GD99'):
        _seed('GD99')
