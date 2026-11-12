"""The Disclaimers tab, last in the file (plan.md §9.4; J151; OQ40 default: the old wording, one constant, until
Stephanie's review; old `disclaimers.py` and `presentation_workbook._DisclaimersSheet` at 891f1b3): the standing
paragraphs, then each carrier's own notes for the carriers in the file. The metal-tier note and the carrier notes
ship empty, as in the old app: an empty entry prints nothing, never another firm's words.
"""

from deals import carriers

from .. import cells
from .. import print_plan as pp
from .. import styles as s
from .common import subtitle

STANDARD = (
    'This comparison is an overview of the plans and rates the carriers quoted for this group, based on the '
    'information they were given. It is not a contract or a guarantee of coverage.',
    "Final rates and benefits depend on the final census, enrollment and participation, and on each carrier's "
    'underwriting approval. They may change before the plan year begins.',
    "Plan designs are summarized. Each carrier's Summary of Benefits and Coverage and policy documents describe the "
    'full benefits, and they govern where anything here differs.',
    'Rates are monthly. Totals are estimates from the enrollment shown and recalculate when the counts are changed.',
)
ACTUARIAL_NOTE = ''  # the metal-tier (actuarial value) wording, from the benefits team (Stephanie; OQ40)
CARRIER_NOTES = {}  # {carrier identity: (note, …)}: each carrier's own rules, as the team supplies them
WIDTH, CHARS = 120, 135


def notes_for(names):
    """[(display name, (note, …))] for the carriers named, first seen first, one per carrier, only where notes exist."""
    found, seen = [], set()
    for name in names:
        identity = carriers.identity(name)
        if not identity or identity in seen:
            continue
        seen.add(identity)
        notes = tuple(note for note in CARRIER_NOTES.get(identity) or () if note)
        if notes:
            found.append((carriers.display_name(name) or str(name), notes))
    return found


def write(sheet, ctx):
    sheet.widths[1] = WIDTH
    cells.band(sheet, 1, 1, 'Disclaimers', size=s.TITLE_SIZE, height=24)
    cells.band(sheet, 2, 1, subtitle(ctx.facts), height=18)
    cells.spacer(sheet, 3)
    row = 3

    def para(text, look=s.BODY):
        nonlocal row
        row += 1
        cells.text(sheet, row, 1, text, font=look, align=s.LEFT_TOP)
        sheet.heights[row] = cells.row_height([(text, CHARS)])

    def heading(text):
        nonlocal row
        row += 1
        cells.spacer(sheet, row)
        para(text, s.BOLD)

    for text in STANDARD:
        para(text)
    if ACTUARIAL_NOTE:
        heading('Metal tiers and actuarial value')
        para(ACTUARIAL_NOTE)
    names = [plan.carrier for line in ctx.facts.lines for plan in line.presented]
    for found in ctx.banks.values():
        names += [entry['carrier'] for entry in found['entries'] if entry['kind'] == 'plan']
    for carrier, notes in notes_for(names):
        heading(carrier)
        for note in notes:
            para(note)
    sheet.zoom = s.ZOOM
    pp.fitted(sheet, 1, row, draft=ctx.draft, best_fit=True)
