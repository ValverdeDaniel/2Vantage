"""One row of the packet grid (plan.md §8.12; K34–K56), the shape every section shares. Pure.

`{key, kind, section, label, sub, file_format, include, default_include, deliberate, packet_eligible, available,
reason, hint, required_by, for_fallback, rows, max_rows, capped, lens, phi, size, …}`: `key` is the one key space's
(K.6); `deliberate` says why a row is off on purpose ("Select all" leaves it alone, K35); `packet_eligible` is False
for the download-only rows; `reason` why a row is unticked or unavailable; `hint` a note under it ("Not signed by the
employer yet"); `phi` whether the file carries member data (its downloads are logged); `size` about how many bytes it
adds to an email (K121).
"""


def card(
    key,
    section,
    label,
    file_format,
    *,
    default=True,
    deliberate='',
    eligible=True,
    available=True,
    reason='',
    hint='',
    sub='',
    for_names=(),
    for_fallback='—',
    rows=None,
    max_rows=None,
    capped=False,
    lens='',
    phi=False,
    size=0,
    **extra,
):
    return {
        'key': key,
        'kind': extra.pop('kind', section),
        'section': section,
        'label': label,
        'sub': sub,
        'file_format': file_format,
        'include': False,
        'default_include': bool(default) and eligible,
        'deliberate': deliberate,
        'packet_eligible': eligible,
        'available': available,
        'reason': reason,
        'hint': hint,
        'required_by': list(for_names),
        'for_fallback': for_fallback,
        'rows': rows,
        'max_rows': max_rows,
        'capped': capped,
        'lens': lens,
        'phi': phi,
        'size': size,
        **extra,
    }
