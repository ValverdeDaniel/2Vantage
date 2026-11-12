"""The spec as the browser reads it: `GET meta/questionnaires/{form}/` (plan.md §7.9; G12, G17, G23, G25). Pure.

No answers in it, so it is cached per form version. It carries the sections and fields with their flags — `required`,
`width`, `hint`, `placement`, `sensitive`, `broker` and `driver` (a question another rule hangs on: Enter or Tab on it
waits for the save's reply, G25) — and the options: a static or flat-table picker's list once (the SIC lists built a
single time, G17), and for a dependent picker its table, read by the option key each row's payload names (G12). The
browser holds no visibility, effect or progress rule: each payload says what is on screen.
"""

from functools import cache

from . import forms
from .engine.narrow import drivers
from .engine.options import flat_options

FIELD_KEYS = ('key', 'label', 'type', 'width', 'hint', 'placement', 'auto', 'depends_on')
BLOCK_KEYS = ('key', 'label', 'row_label', 'add_label', 'empty_label', 'min_rows', 'max_rows')
SECTION_KEYS = ('key', 'number', 'label', 'intro', 'intro_after_fields', 'legend', 'legend_intro')


def _field(form, block_key, field, driving):
    out = {name: field[name] for name in FIELD_KEYS if field.get(name) not in (None, '')}
    out['required'] = bool(field.get('required'))
    out.setdefault('width', 1)
    if field.get('options'):
        out['options'] = list(field['options'])
    elif field.get('options_from') and not field.get('depends_on'):
        out['options'] = flat_options(form, field)
    elif field.get('depends_on'):
        out['options_table'] = field['options_from']
    if forms.is_sensitive(form['key'], block_key, field['key']):
        out['sensitive'] = True
    if field.get('broker'):
        out['broker'] = True
    if field.get('prefill'):
        out['prefills'] = True
    if (block_key, field['key']) in driving:
        out['driver'] = True
    return out


@cache
def spec(key):
    """The browser's copy of one form (G.6 endpoint `meta/questionnaires/{form}/`)."""
    form = forms.FORMS[key]
    driving = drivers(form)
    dependent = {f['options_from'] for b in form['blocks'].values() for f in b['fields'] if f.get('depends_on')}
    return {
        'key': form['key'],
        'version': form['version'],
        'kind': form['kind'],
        'item': forms.item_of(form),
        'carrier': form['carrier'],
        'short_label': forms.label(key),
        'title': form['title'],
        'subtitle': form['subtitle'],
        'export_slug': form['export_slug'],
        'officer_label': form['officer_label'],
        'has_blank_pdf': bool(form.get('blank_pdf')),
        'sections': [
            {
                **{name: section.get(name) or ('' if name != 'legend' else []) for name in SECTION_KEYS},
                'fields': [_field(form, '', f, driving) for f in section.get('fields') or []],
                'blocks': list(section.get('blocks') or []),
            }
            for section in form['sections']
        ],
        'blocks': {
            block_key: {
                **{name: block.get(name, '') for name in BLOCK_KEYS},
                'sensitive': bool(block.get('sensitive')),
                'fields': [_field(form, block_key, f, driving) for f in block['fields']],
            }
            for block_key, block in form['blocks'].items()
        },
        'tables': {name: form['tables'][name] for name in sorted(dependent)},
    }
