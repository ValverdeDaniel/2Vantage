"""Start-up checks (G1, G124, G125): Django system checks, run by `manage.py check`, `migrate` and the dev server.

- the bundled Florida Blue blank is the one the stamp geometry was measured on (`fl_blue_51_layout.BLANK_SHA256`), so
  a reissued carrier form fails loudly instead of stamping into empty space (G125);
- the bundled template is the one the data module was generated from (`fl_blue_51_data.SOURCE_SHA256`; G124);
- every alias names a label the pickers offer and opens a branch of the carrier's tables (G12; a category with no
  conditions, such as Diabetes, is the carrier's own: its row shows no condition picker);
- every form's bundled blank is present.
"""

import hashlib

from django.core.checks import Error, register

from .forms import FORMS, asset_path, fl_blue_51_data, fl_blue_51_layout

TEMPLATE = 'fl_blue_51_uw_v9.template.xml'


def _sha(name, text=False):
    """The file's SHA-256; a text file's with CRLF read as LF, so a Windows checkout (core.autocrlf) still matches."""
    path = asset_path(name)
    if not path:
        return None
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b'\r\n', b'\n') if text else data).hexdigest()


def problems():
    """[sentence] of what is out of step; [] when every check passes."""
    found = []
    if _sha(fl_blue_51_layout.BLANK_FILE) != fl_blue_51_layout.BLANK_SHA256:
        found.append(f'{fl_blue_51_layout.BLANK_FILE} is not the blank the stamp layout was measured on.')
    if _sha(TEMPLATE, text=True) != fl_blue_51_data.SOURCE_SHA256:
        found.append(f'{TEMPLATE} is not the template fl_blue_51_data.py was generated from.')
    form = FORMS['fl_blue_51']
    tables, aliases = form['tables'], form['aliases']
    for label, target in aliases['category'].items():
        if label not in tables['med_categories'] or target not in tables['conditions_by_category']:
            found.append(f'The category alias "{label}" opens no branch of the carrier tables.')
    for label, target in aliases['condition'].items():
        if target not in tables['details_by_condition']:
            found.append(f'The condition alias "{label}" opens no branch of the carrier tables.')
    for key, spec in FORMS.items():
        if spec.get('blank_pdf') and asset_path(spec['blank_pdf']) is None:
            found.append(f'The blank of {key} is missing from assets/questionnaires.')
    return found


@register()
def questionnaire_assets(app_configs, **kwargs):
    return [Error(sentence, id='questionnaire.E001') for sentence in problems()]
