"""What other apps ask quotes about sales (plan.md §5.1, §3.3)."""

from ..models import Plan


def client_has_sold(client_id):
    """Whether any plan on any of the client's deals is sold: fills `deals.providers.client_has_sold`."""
    return Plan.objects.filter(deal__client_id=client_id, sold=True).exists()
