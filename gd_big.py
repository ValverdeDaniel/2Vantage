"""GD-Big (plan.md §13.4, Q.7): one synthetic deal at scale, for the query-scaling tests and the Perf lane.

Tests only: `seed_golden` never builds it, and only the root conftest imports it. 600 plans through the services would
take most of the Fast lane's budget, so the rows are bulk-created as the services would leave them: values cleaned as
§5.4 stores them, each read from one of the deal's documents (origin `ai`, page, printed line and read value, half of
them approved), links, stars, recommendations, typed counts and member-built packages. `build(user, plans=10)` makes
the same shape small, so a scaling test compares two sizes and never pins a number (Q.3 #4). All data is synthetic.
"""

import random

from deals import clock
from deals.services import create_client, delete_client
from documents.models import Document
from intake.services import set_intent
from quotes.models import Package, Plan

NAME = 'GD-Big (synthetic)'
CURRENTS = 4
CARRIERS = ['Aetna', 'Cigna', 'UnitedHealthcare', 'Florida Blue', 'Humana', 'AvMed', 'Oscar', 'Ambetter']
DESIGN = {
    'network': ['Open Access', 'Choice Plus', 'LocalPlus', 'BlueOptions', 'Navigate'],
    'plan_type': ['PPO', 'HMO', 'HDHP', 'EPO', 'POS'],
    'metal_level': ['Bronze', 'Silver', 'Gold', 'Platinum'],
    'funding': ['fully_insured', 'level_funded'],
    'minimum_value': ['Yes', 'No'],
    'part_d_creditable': ['Yes', 'No'],
    'deductible_type': ['Embedded', 'Aggregate'],
    'telehealth': ['$0', '$0 after deductible', '$10'],
    'inpatient': ['Deductible, then 20%', '$500 per admit', '20% after deductible'],
    'outpatient_surgery': ['Deductible, then 20%', '$250 copay'],
    'diagnostic_test': ['$0', 'Deductible, then 20%'],
    'advanced_imaging': ['$250', 'Deductible, then 30%'],
    'rx_deductible': ['Integrated', 'None', '$250'],
    'rx_mail_order': ['2.5x retail', '3x retail'],
}
AMOUNTS = {
    'deductible_single': (500, 7000),
    'deductible_family': (1000, 14000),
    'deductible_single_oon': (1000, 14000),
    'oop_max_single': (2000, 9100),
    'oop_max_family': (4000, 18200),
    'coinsurance': (0, 50),
    'pcp_copay': (0, 60),
    'specialist_copay': (10, 120),
    'urgent_care_copay': (25, 150),
    'er_copay': (150, 750),
    'rx_t1': (0, 25),
    'rx_t2': (15, 75),
    'rx_t3': (40, 150),
    'rx_t4': (100, 500),
}
RATES = {'rate_ee': (380, 900), 'rate_es': (800, 1900), 'rate_ec': (700, 1700), 'rate_fam': (1200, 2800)}


def _values(rng):
    values = {key: rng.choice(choices) for key, choices in DESIGN.items()}
    values.update({key: str(rng.randrange(low, high, 5)) for key, (low, high) in AMOUNTS.items()})
    values.update({key: f'{rng.uniform(low, high):.2f}' for key, (low, high) in RATES.items()})
    values['sbc_url'] = f'https://example.com/sbc/{rng.randrange(10**6)}.pdf'
    return values


def _sources(rng, values, documents, user, at):
    sources = {}
    for key, value in values.items():
        entry = {'origin': 'ai', 'by': user.id, 'at': at, 'doc': rng.choice(documents), 'page': rng.randrange(1, 9)}
        entry.update({'line': f'{key.replace("_", " ").title()} {value}'[:80], 'read_value': value})
        if rng.random() < 0.5:
            entry['confirmed'] = {'by': user.id, 'at': at, 'via': 'review'}
        sources[key] = entry
    return sources


def build(user, plans=600, name=NAME, seed=7):
    """The deal, with `plans` medical plans: CURRENTS current plans, each with a renewal, and the rest alternates;
    about a third of the alternates replace a current plan, a tenth are starred, a few are recommended."""
    rng = random.Random(seed)
    _, deal = create_client(user, name=name)
    set_intent(user, deal.id, lines=['medical', 'dental', 'vision'], shop=True)
    deal.refresh_from_db()
    files = [Document(deal=deal, original_name=f'quote-{n}.pdf', kind='quote', uploaded_by=user) for n in range(20)]
    documents = [doc.id for doc in Document.objects.bulk_create(files)]
    at = clock.now().isoformat()

    def row(index, role, **marks):
        values = _values(rng)
        return Plan(
            deal=deal,
            line='medical',
            role=role,
            carrier=CARRIERS[0] if role != 'alternate' else rng.choice(CARRIERS),
            name=f'{values["plan_type"]} {values["deductible_single"]} #{index}',
            values=values,
            sources=_sources(rng, values, documents, user, at),
            enrollment={'EE': rng.randrange(5, 40), 'ES': rng.randrange(0, 10), 'EC': 3, 'FAM': 4},
            enrollment_on=role == 'current',
            sort_order=index,
            **marks,
        )

    currents = Plan.objects.bulk_create(row(index, 'current') for index in range(CURRENTS))
    renewals = [row(CURRENTS + n, 'renewal', renews_id=current.id) for n, current in enumerate(currents)]
    room, alternates = 16 - CURRENTS - 2, []
    for index in range(2 * CURRENTS, plans):
        starred = room > 0 and rng.random() < 0.1
        room -= starred
        alternates.append(
            row(
                index,
                'alternate',
                starred=starred,
                star_reason='Hand-picked' if starred else '',
                starred_by_id=user.id if starred else None,
                recommended=index < 2 * CURRENTS + 2,
            )
        )
    Plan.objects.bulk_create(renewals)
    alternates = Plan.objects.bulk_create(alternates)
    links = Plan.replaces.through
    linked = [plan for plan in alternates if rng.random() < 0.34]
    links.objects.bulk_create([links(from_plan_id=plan.id, to_plan_id=rng.choice(currents).id) for plan in linked])
    for number in range(3):
        package = Package.objects.create(deal=deal, line='medical', name=f'Package {number}', sort_order=number)
        package.plans.set(rng.sample(alternates, min(3, len(alternates))))
    deal.refresh_from_db()
    return deal


def remove(user, deal):
    delete_client(user, deal.client_id)
