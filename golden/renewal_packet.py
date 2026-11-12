"""GD3's renewal packet (plan.md §13.4; slice 18): a synthetic Florida Blue renewal printing the two current plans
that arrive (`arrivals` D and F) and their renewals, in that order, with the per-plan enrolled counts the packet
prints, built from the spec by the quote reader's own printer (quotes/reader/printed.py), so the file and the answer
a perfect read gives come from one place. The seed attaches it to the deal unread; a read of it on Documents stages
the change set (the done-when of slice 18), and `answer(spec)` is the reply the fake client replays in tests.
"""

from django.core.files.uploadedfile import SimpleUploadedFile

from documents import services as documents
from quotes.reader import corpus, printed

DESIGN_KEYS = ('plan_type', 'network', 'metal_level', 'deductible_single', 'oop_max_single', 'pcp_copay')
TIER_KEYS = ('rate_ee', 'rate_es', 'rate_ec', 'rate_fam')
RANGE = 'p1-2'  # the cover and the table: the last page carries only the running header and footer


def table(spec):
    packet = spec['renewal_packet']
    columns, counts = [], {}
    for arrival in spec['arrivals']:
        design = {key: arrival['values'][key] for key in DESIGN_KEYS if arrival['values'].get(key)}
        current = tuple(arrival['values'][key] for key in TIER_KEYS)
        renewal = tuple(packet['renewals'][arrival['ref']][key] for key in TIER_KEYS)
        counts[len(columns)] = dict(arrival.get('enrollment') or {})
        columns.append(corpus.medical(arrival['name'], 'current', design, current, carrier=packet['carrier']))
        columns.append(
            corpus.medical(
                arrival['name'], 'renewal', design, renewal, carrier=packet['carrier'], renews=len(columns) - 1
            )
        )
    return corpus.table('medical', packet['carrier'], packet['title'], columns, counts)


def packet_pdf(spec):
    return printed.pdf([table(spec)])


def answer(spec):
    """The reply of a perfect read of the packet's pages 1–2, in the quote reader's schema."""
    return corpus.answer_of(table(spec))


def attach(user, deal, spec):
    """Upload GD3's packet unread (kind renewal, role renewal). It prints no plan the seed makes, so {}."""
    packet = spec.get('renewal_packet')
    if packet:
        documents.upload(
            user,
            deal,
            SimpleUploadedFile(packet['file'], packet_pdf(spec)),
            {'kind': 'renewal', 'role': 'renewal', 'carrier': packet['carrier'], 'lines': ['medical']},
        )
    return {}
