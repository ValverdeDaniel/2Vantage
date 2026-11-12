"""What the RFP tab tells others (plan.md §6.10; K117, J63; N.3 "Who was asked").

`asked_by_line(deal)`: who was asked for each line, from the sends marked on the Emails card (`RfpRequest.sends`, the
frozen record a send stores). Proposals' Markets checked reads it directly (rfp sits left of proposals). Ported from old
Vantage 891f1b3 `pipeline/markets._asked_by_line` (over `rfp_config['asked']`): each carrier once per line, the first
mention winning, a registry carrier by its key and any other by `deals.carriers.identity` of its name. A deal with no
RfpRequest, or none of its drafts marked sent, answers {}: "no RFP sent" (one light query, no row made).
"""

from deals import carriers

from .models import RfpRequest


def _sends(stored):
    """The sends in the order they happened: by send date, then the stamp, then the draft key (never the JSON order,
    which Postgres does not keep)."""
    entries = [(key, send) for key, send in (stored or {}).items() if isinstance(send, dict)]
    return sorted(entries, key=lambda item: (str(item[1].get('on') or ''), str(item[1].get('at') or ''), item[0]))


def asked_from(sends):
    """{line: [{id, name, on}]} from stored sends (pure): `id` is the carrier's identity (its registry key, or 'n:…'
    for a name the registry does not know), `name` as written on the draft, `on` the first send's date."""
    out, seen = {}, set()
    for _key, send in _sends(sends):
        for entry in send.get('asked') or []:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get('name') or '').strip()
            identity = entry.get('key') or carriers.identity(name)
            if not identity:
                continue
            for line in entry.get('lines') or []:
                if (line, identity) in seen:
                    continue
                seen.add((line, identity))
                out.setdefault(line, []).append({'id': identity, 'name': name, 'on': send.get('on') or ''})
    return out


def asked_by_line(deal):
    """{line: [{id, name, on}]} for the deal; {} until an RFP is sent."""
    deal_id = getattr(deal, 'pk', deal)
    sends = RfpRequest.objects.filter(deal_id=deal_id).values_list('sends', flat=True).first()
    return asked_from(sends)
