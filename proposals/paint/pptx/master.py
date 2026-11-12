"""The slide master and its four layouts (plan.md §9.6; J139, J141). Ported from old Vantage 891f1b3
`pipeline/proposal_deck.py` (`_dress_look_master`, `_style_look_title`, `_dress_theme`, `_lift`), the D-178
Presentation format's master; the old app shipped no .pptx template, it dressed python-pptx's own, as this does.

- **Proposal content**: the master holds what every content page wears, lifted from the recorded chrome once (the
  rule, the footer bar, the logo or the mark, the stamp, the rates note, the firm, Draft), and the title placeholder
  in the title zone, 26 pt bold in the brand's navy; change the master and every content slide follows.
- **Proposal dark page**: the dark ground with the mark (the agenda, a divider; the cover and Thank you without a
  picture). **Proposal photo page**: the ground without the mark, for a dark page with a picture in its frame.
- **Proposal plain page**: a white page with nothing of the master's (the old Classic covers, J143, deferred).
The theme carries the brand as accent 1 and Arial everywhere, so a native chart or a new shape picks them up.
"""

from lxml import etree
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn

from ...layout import tokens
from . import frames
from .units import FAMILY, emu, hex_value

NAMES = {
    'dark': 'Proposal dark page',
    'plain': 'Proposal plain page',
    'photo': 'Proposal photo page',
    'content': 'Proposal content',
}
# python-pptx's own layouts the four are made from. Not its third: that title is all capitals, in PowerPoint alone.
FROM = {'dark': 0, 'plain': 1, 'photo': 3, 'content': 5}


def _style_title(master, navy):
    """Every content slide's title reads from the master: its place (the title zone), its type and its colour."""
    for holder in master.placeholders:
        if holder.placeholder_format.idx == 0:
            holder.left, holder.top = emu(tokens.PAGE_MARGIN), emu(tokens.TITLE_TOP)
            holder.width = emu(tokens.PAGE_W - 2 * tokens.PAGE_MARGIN)
            holder.height = emu(tokens.TITLE_HEIGHT)
            body = holder._element.txBody.find(qn('a:bodyPr'))
            body.set('lIns', '0')
            body.set('anchor', 'ctr')
    level = master._element.find(qn('p:txStyles')).find(qn('p:titleStyle')).find(qn('a:lvl1pPr'))
    level.set('algn', 'l')
    defaults = level.find(qn('a:defRPr'))
    defaults.set('sz', str(int(tokens.TITLE_TYPE[0] * 100)))
    defaults.set('b', '1')
    defaults.set('kern', '0')  # unkerned, as the layout measured it (units.unkerned)
    for child in list(defaults):
        defaults.remove(child)
    fill = etree.SubElement(defaults, qn('a:solidFill'))
    etree.SubElement(fill, qn('a:srgbClr'), val=hex_value(navy))
    etree.SubElement(defaults, qn('a:latin'), typeface=FAMILY)


def _dress_theme(master, colours):
    part = master.part.part_related_by(RT.THEME)
    root = etree.fromstring(part.blob)
    scheme = root.find('.//' + qn('a:clrScheme'))
    for tag, value in (('a:accent1', colours['navy']), ('a:accent2', colours['ink2']), ('a:dk2', colours['ink'])):
        slot = scheme.find(qn(tag))
        for child in list(slot):
            slot.remove(child)
        etree.SubElement(slot, qn('a:srgbClr'), val=hex_value(value))
    for font in root.iter(qn('a:latin')):
        font.set('typeface', FAMILY)
    part._blob = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def _relink(element, scratch, target):
    """A moved element's pictures and links point at parts of the scratch slide: relate them to `target` too."""
    for blip in element.iter(qn('a:blip')):
        image = scratch.part.related_part(blip.get(qn('r:embed')))
        blip.set(qn('r:embed'), target.part.relate_to(image, RT.IMAGE))
    for link in element.iter(qn('a:hlinkClick')):
        old = link.get(qn('r:id'))
        if old:
            address = scratch.part.target_ref(old)
            link.set(qn('r:id'), target.part.relate_to(address, RT.HYPERLINK, is_external=True))


def _lift(prs, layout, target, placed, pictures):
    """Paint `placed` on the layout or master `target`, beneath its placeholders. python-pptx adds shapes only to a
    slide, so they are painted on a scratch slide and moved up; the scratch slide is then dropped."""
    scratch = prs.slides.add_slide(layout)
    for item in placed:
        frames.paint(scratch, item, pictures)
    tree = target.shapes._spTree
    insert_at = 2  # after the group's own properties
    for offset, shape in enumerate(list(scratch.shapes)):
        if shape.is_placeholder:
            continue
        element = shape._element
        element.xpath('.//p:cNvPr')[0].set('id', str(100 + offset))
        _relink(element, scratch, target)
        element.getparent().remove(element)
        tree.insert(insert_at, element)
        insert_at += 1
    slide_ids = prs.slides._sldIdLst
    entry = slide_ids[-1]
    prs.part.drop_rel(entry.rId)
    slide_ids.remove(entry)


def _layouts(prs):
    every = list(prs.slide_layouts)
    chosen = {key: every[number] for key, number in FROM.items()}
    for layout in every:
        if layout not in chosen.values():
            prs.slide_layouts.remove(layout)
    for key, layout in chosen.items():
        layout.name = NAMES[key]
    return chosen


def dress(prs, colours, chrome, grounds, pictures):
    """Dress `prs`'s master: `chrome` the frames every content page shares, `grounds` {'dark', 'photo'} the dark
    pages' grounds. → {'dark', 'plain', 'photo', 'content'}: the layouts."""
    master = prs.slide_master
    layouts = _layouts(prs)
    # Only the title remains: the chrome replaces the rest (the old master kept its body placeholder too).
    for holder in list(master.placeholders):
        if holder.placeholder_format.idx not in (0, 1):
            holder._element.getparent().remove(holder._element)
    for layout in layouts.values():
        for holder in list(layout.placeholders):
            if holder.placeholder_format.idx != 0:
                holder._element.getparent().remove(holder._element)
            else:  # inherit the master's place, not the template's 4:3 one
                properties = holder._element.spPr
                for child in list(properties):
                    properties.remove(child)
    _style_title(master, colours['navy'])
    _dress_theme(master, colours)
    for key in ('dark', 'plain', 'photo'):
        layouts[key]._element.set('showMasterSp', '0')
    _lift(prs, layouts['content'], master, chrome, pictures)
    _lift(prs, layouts['dark'], layouts['dark'], grounds['dark'], pictures)
    _lift(prs, layouts['photo'], layouts['photo'], grounds['photo'], pictures)
    return layouts
