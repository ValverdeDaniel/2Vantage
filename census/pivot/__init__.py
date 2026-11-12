"""The reformat of a one-row-per-benefit census (plan.md §5.3.2 step 3; C13, C15).

`reshape(table, reformat)` scores the table's shape (`shape.detect`): from 0.80 it is reformatted to one row per person
(`rows.reshape`); from 0.55 to 0.80 it is flagged "needs attention" and mapped as it is. Only the recipe is stored on
the import; the rows are rebuilt from the file each time, so a 1,000-person file is never kept twice. The things worth
checking name people, so they are worked out again for each answer and never stored.
"""

from ..importer.read import Table
from . import rows, shape

ATTENTION = (
    "This census may be one row per benefit, but we couldn't confirm it. Map the columns below, or send it back to "
    'be reformatted.'
)
STORED = (
    'applied',
    'declined',
    'reason',
    'confidence',
    'signals',
    'line_column',
    'line_column_header',
    'label_map',
    'lines',
    'unknown_lines',
    'source_rows',
    'employee_rows',
    'dependent_rows',
)


def _recipe(detection, result=None, **extra):
    result = result or {}
    recipe = {
        'applied': bool(result.get('applied')),
        'declined': False,
        'reason': result.get('reason', ''),
        'confidence': detection['confidence'],
        'signals': detection['signals'],
        'line_column': detection['line_column'],
        'line_column_header': detection['line_column_header'],
        'label_map': detection['label_map'],
        'lines': result.get('lines', []),
        'unknown_lines': detection['unknown_labels'],
        'source_rows': result.get('source_rows', 0),
        'employee_rows': result.get('employee_rows', 0),
        'dependent_rows': result.get('dependent_rows', 0),
    }
    recipe.update(extra)
    return {key: recipe[key] for key in STORED}


def reshape(table, reformat=True):
    """(the table to map, the recipe to store, the things worth checking). `reformat` False: the member chose the
    original file ("Use the original file instead"), so a reformattable file is mapped as uploaded."""
    if not table.rows:
        return table, {}, []
    detection = shape.detect(table.headers, table.rows)
    if detection['confidence'] < shape.SUSPECT:
        return table, {}, []
    if detection['confidence'] < shape.CONFIDENT:
        return table, _recipe(detection, reason=ATTENTION), []
    result = rows.reshape(table.headers, table.rows, detection)
    conflicts = result.get('conflicts', [])
    if not result['applied']:
        return table, _recipe(detection, result), conflicts
    if not reformat:
        return table, _recipe(detection, result, applied=False, declined=True), []
    return Table(table.sheet, result['headers'], result['rows'], []), _recipe(detection, result), conflicts


def needs_attention(recipe):
    return bool(recipe) and not recipe.get('applied') and bool(recipe.get('reason'))
