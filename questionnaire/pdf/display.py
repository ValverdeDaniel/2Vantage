"""How one answer reads on a carrier's page (G57, G59). Pure.

- `boxed`: the stamped flat form's boxes, as the carrier's own boxes read — dates MM/DD/YYYY, money with a dollar sign
  and cents, a percentage with its sign, a picker printed through its `display_map` (State saves "FL", the carrier's
  box reads "Florida"). Blank stays blank: an empty box on a carrier form means unanswered.
- `handwritten`: an AcroForm's fields, as a person filling the form by hand writes them — dates MM/DD/YYYY, money
  as "1,000,000" (the form prints its own $), the coverage-status letter through `display_map`.
- `listed`: an attachment page's answers, where a blank prints as an em dash so it reads as unanswered.
Ported from old Vantage 891f1b3 (`questionnaire_stamp._display`, `questionnaire_acroform._display`,
`questionnaire_pdf._fmt`).
"""

from datetime import date


def _raw(value):
    return '' if value is None else str(value).strip()


def us_date(text):
    """ISO date -> MM/DD/YYYY; anything else passes through (a client may have typed '3/2025')."""
    try:
        return date.fromisoformat(text).strftime('%m/%d/%Y')
    except ValueError:
        return text


def _mapped(field, raw):
    mapping = (field or {}).get('display_map')
    return str(mapping.get(raw, raw)) if mapping else None


def _typed(field, raw):
    kind = (field or {}).get('type', 'text')
    if kind == 'money':
        try:
            return f'${float(raw.replace(",", "").replace("$", "")):,.2f}'
        except ValueError:
            return raw
    if kind == 'percent':
        return raw if raw.endswith('%') else f'{raw}%'
    if kind == 'date':
        return us_date(raw)
    return raw


def boxed(field, value):
    raw = _raw(value)
    if not raw:
        return ''
    mapped = _mapped(field, raw)
    return mapped if mapped is not None else _typed(field, raw)


def handwritten(field, value):
    raw = _raw(value)
    if not raw:
        return ''
    mapped = _mapped(field, raw)
    if mapped is not None:
        return mapped
    kind = (field or {}).get('type', 'text')
    if kind == 'date':
        return us_date(raw)
    if kind == 'money':
        digits = raw.replace(',', '').replace('$', '').strip()
        return f'{int(digits):,}' if digits.isdigit() else raw
    return raw


def listed(field, value):
    raw = _raw(value)
    return _typed(field, raw) if raw else '—'
