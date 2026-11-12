"""The census cells the RFP's files require (plan.md §5.3.3 step 6; K124): rfp fills census's `carrier_required`
provider slot with `carrier_required(deal_id)` at start-up (O.1), so a blank a carrier's file needs is flagged on the
Census tab before the file is filled, and "Census OK" means "the files you are about to send are complete".

`required_columns(request, requested_lines)` is pure over the request, the definitions and the requested lines; it
reads no census: `{census key: {employee: [names], dependent: [names]}}` over the formats the request sends
(`scope.sent`), the names saying whose file needs the cell. A column counts when the carrier requires it
(`translate.column_required`, the one rule) and it holds a census key: its own `field`, or what a derived column reads
by value (UHC's required "Out of Area" reads the ZIP). An employee-only column, a line the deal is not quoting and a
dependent's medical tier never ask anything of a dependent; a dependent's blank inherited ZIP takes the employee's.
"""

from census import fields
from deals.models import Deal

from .. import cleaners
from ..models import RfpRequest
from . import definitions, describe, scope, translate


def _keys(column):
    """The census keys a required column needs a value in."""
    if column.get('field'):
        return [column['field']]
    return [key for key, how in describe.consumes(column) if how == 'value' and key in fields.BY_KEY]


def _kinds(column, quoted):
    line = column.get('line') or ''
    if line and quoted and line not in quoted:
        return ()
    if column.get('employee_only'):
        return (fields.EMPLOYEE,)
    field = column.get('field') or ''
    if column.get('inherits') or field in ('medical_tier', 'effective_date'):
        return (fields.EMPLOYEE,)
    return (fields.EMPLOYEE, fields.DEPENDENT)


def required_columns(request, requested_lines):
    """{census key: {employee: [names], dependent: [names]}}; {} when the request sends no carrier's file."""
    quoted = set(requested_lines or ())
    out = {}
    for fmt_key, names in scope.sent(request).items():
        for column in definitions.DEFINITIONS[fmt_key]['columns']:
            if not translate.column_required(column):
                continue
            for key in _keys(column):
                for kind in _kinds(column, quoted):
                    found = out.setdefault(key, {fields.EMPLOYEE: [], fields.DEPENDENT: []})[kind]
                    found.extend(name for name in names if name not in found)
    return out


def carrier_required(deal_id):
    """census.providers.carrier_required: the deal's answer, from its stored request and requested lines."""
    row = RfpRequest.objects.filter(deal_id=deal_id).first()
    if row is None:
        return {}
    requested = Deal.objects.filter(pk=deal_id).values_list('requested_lines', flat=True).first() or []
    return required_columns(cleaners.stored(row), requested)
