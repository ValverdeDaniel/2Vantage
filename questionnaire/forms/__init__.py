"""The carrier forms and their catalogue (plan.md §6.8, §8.11; G1, G3, G4, G23). Pure: no database.

`FORMS` is the registry of the three specs: Florida Blue 51+ (the medical band default at 51 or more enrolled),
Warner Pacific 51+ (a medical pick) and the SIIA stop-loss disclosure (a stop-loss opt-in). The catalogue — which
checklist item each form rides, the choices each item's picker offers with their long and short labels, and the band
default — is served by /api/meta/ as `questionnaires` (rule 1), so every picker reads one list (G3).

The stored choices are explicit (G4's fix of the old `none`): on the medical item `auto` (the band decides), a form
key, or `upload` (no fillable form, upload only); on the stop-loss item `''` (not needed), a form key, or `upload`
(needed, upload only). The old `none` reads as `upload`.

The catalogue lives here, beside the registry it lists, rather than as a copy in intake (G1's design): intake stores
the choice (`intake.services.set_form_choice`) and reads this app's answer through `intake.providers.
questionnaire_items`, so one list serves both and no start-up check has to keep two in step.
"""

from functools import cache
from pathlib import Path

from intake.checklist import QUESTIONNAIRE, STOP_LOSS

from . import fl_blue_51_data, fl_blue_51_layout  # noqa: F401 (the start-up checks read them)
from .fl_blue_51 import FORM as FL_BLUE_51
from .stop_loss_siia import FORM as STOP_LOSS_SIIA
from .wp_lg import FORM as WP_LG

FORMS = {form['key']: form for form in (FL_BLUE_51, WP_LG, STOP_LOSS_SIIA)}
ASSETS = Path(__file__).resolve().parents[2] / 'assets' / 'questionnaires'

MEDICAL, STOP_LOSS_KIND = 'medical', 'stop_loss'
ITEMS = {QUESTIONNAIRE: MEDICAL, STOP_LOSS: STOP_LOSS_KIND}  # checklist item → the kind of form it rides
# A filled copy's document kind (documents/kinds.py), by the kind of form it is: what Claude's reader reads into the
# form (slice 52; the old "a qform read's type follows its form").
FILE_KIND = {MEDICAL: 'questionnaire', STOP_LOSS_KIND: 'stop_loss'}
ITEM_OF_KIND = {kind: item for item, kind in ITEMS.items()}
AUTO, UPLOAD, NOT_NEEDED, OLD_NONE = 'auto', 'upload', '', 'none'

# The size band's default form per item (G5; OQ53: 51 or more enrolled is large). Stop-loss is opt-in (OQ58).
LARGE_AT = 51
BAND_DEFAULTS = {QUESTIONNAIRE: {'large': FL_BLUE_51['key'], 'small': ''}, STOP_LOSS: {'large': '', 'small': ''}}
BAND_WORDS = {'large': '51+', 'small': '≤50'}

# The choices' words (G3), as old Vantage's checklist and Overview (long) and coverage panel (short) printed them.
AUTO_LABEL = 'Auto by group size'
UPLOAD_LABELS = {
    QUESTIONNAIRE: ('No fillable form — upload only', 'No fillable form'),
    STOP_LOSS: ('Needed — upload only', 'Upload only'),
}
NOT_NEEDED_LABELS = ('Not needed for this group', 'Not needed')
SIGNED_LOCK = 'Signed — the form can no longer be swapped.'


def get_form(key):
    """A form spec, or None for an unknown key."""
    return FORMS.get(key or '')


def label(key):
    form = get_form(key)
    return (form.get('short_label') or form['carrier']) if form else ''


def item_of(form):
    """The checklist item a form rides."""
    return ITEM_OF_KIND[form['kind']]


def forms_of(item):
    """The form keys an item's picker offers, in registry order."""
    return [key for key, form in FORMS.items() if ITEMS.get(item) == form['kind']]


def band(count):
    """'large' at 51 or more enrolled, else 'small' (OQ53: at exactly 50 the band is small)."""
    return 'large' if (count or 0) >= LARGE_AT else 'small'


def band_default(item, count):
    """The form the band picks for an item, or '' (upload only on the medical item; not needed on stop-loss)."""
    return BAND_DEFAULTS[item][band(count)]


def normal_choice(item, raw):
    """A stored choice in today's words: the old `none` is `upload`; a blank medical choice is `auto`."""
    choice = str(raw or '').strip()
    if choice == OLD_NONE:
        return UPLOAD
    if item == QUESTIONNAIRE and choice == '':
        return AUTO
    return choice


def choices(item):
    """The choice keys an item accepts."""
    first = [AUTO] if item == QUESTIONNAIRE else [NOT_NEEDED]
    return [*first, *forms_of(item), UPLOAD]


def options(item):
    """[{key, label, short}] for an item's picker, in the old order (G3)."""
    if item == QUESTIONNAIRE:
        first = {'key': AUTO, 'label': AUTO_LABEL, 'short': AUTO_LABEL}
        forms = [{'key': key, 'label': label(key), 'short': label(key)} for key in forms_of(item)]
    else:
        first = {'key': NOT_NEEDED, 'label': NOT_NEEDED_LABELS[0], 'short': NOT_NEEDED_LABELS[1]}
        forms = [{'key': key, 'label': f'Needed — {label(key)}', 'short': label(key)} for key in forms_of(item)]
    long_upload, short_upload = UPLOAD_LABELS[item]
    return [first, *forms, {'key': UPLOAD, 'label': long_upload, 'short': short_upload}]


def asset_path(name):
    """The bundled file's Path, or None when it is missing."""
    path = ASSETS / name if name else None
    return path if path is not None and path.is_file() else None


@cache
def sensitive_slots(key):
    """{(block, field)} of a form's medical-history and claimant slots (G23): every field marked `sensitive`, and
    every field of a block marked `sensitive` as (block, None). Their values never reach Activity, logs or URLs."""
    form = FORMS[key]
    out = set()
    for section in form['sections']:
        out.update(('', field['key']) for field in section.get('fields') or [] if field.get('sensitive'))
    for block_key, block in (form.get('blocks') or {}).items():
        if block.get('sensitive'):
            out.add((block_key, None))
        out.update((block_key, field['key']) for field in block['fields'] if field.get('sensitive'))
    return frozenset(out)


def is_sensitive(key, block, field):
    slots = sensitive_slots(key)
    return (block or '', None) in slots or (block or '', field) in slots


def meta():
    """/api/meta/ `questionnaires`: the forms, the items they ride and each item's choices (G1, G3)."""
    return {
        'forms': [
            {
                'key': key,
                'kind': form['kind'],
                'file_kind': FILE_KIND[form['kind']],
                'label': label(key),
                'carrier': form['carrier'],
                'title': form['title'],
                'version': form['version'],
            }
            for key, form in FORMS.items()
        ],
        'items': [{'key': item, 'kind': kind, 'options': options(item)} for item, kind in ITEMS.items()],
        'large_at': LARGE_AT,
        'signed_lock': SIGNED_LOCK,
    }
