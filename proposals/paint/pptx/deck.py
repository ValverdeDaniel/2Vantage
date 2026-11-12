"""The client PowerPoint: the recorded pages replayed as slides, one slide a page (plan.md §9.6; J122, J141, J142).
Ported from old Vantage 891f1b3 `pipeline/proposal_deck._paint`, without its second recorder: `layout/record.lay_out`
already logged every frame, and the PDF draws the same ones (`paint/pdf.py`), so a figure, a plan, a caption or a
disclaimer can never differ between the two files. No layout happens here.

- A content page stands on the "Proposal content" layout: the master already wears its shared chrome; its title goes
  in the title placeholder; its page number is a live field; its frames follow, in the order they were recorded.
- A whole page (the cover, the agenda, a divider, Thank you) stands on the layout that holds its recorded ground:
  "Proposal dark page" (the ground and the mark), "Proposal photo page" (the ground alone, a picture in its frame) or
  "Proposal plain page"; its title frame fills the title placeholder where it was recorded.
- Each page's notes are the slide's speaker notes: the producer's reasons and the page's own figures.
"""

import io

from pptx import Presentation

from ...layout import furniture, items, tokens
from . import frames, master, shapes, text
from .units import emu


def _colours(pages):
    """The brand's palette, read back from the ground the deck recorded (the cover always stands on it)."""
    for page in pages:
        found = page['frames']
        if page['kind'] == 'full' and found and found[0]['t'] == 'gradient':
            return furniture.palette(found[0]['bottom'])
    return furniture.palette()


def _grounds(colours):
    return {'dark': furniture.dark_ground(colours, mark=True), 'photo': furniture.dark_ground(colours, mark=False)}


def chrome_parts(page):
    """A content page's chrome as (title, number, shared): its title frame, its page number's frame and the frames
    every content page wears alike, which the master holds."""
    title = number = None
    shared = []
    for it in page.get('chrome') or []:
        if it['t'] == 'text' and it.get('title') and title is None:
            title = it
        elif it['t'] == 'text' and number is None and items.plain(it) == str(page.get('n')):
            number = it
        else:
            shared.append(it)
    return title, number, shared


def layout_of(page, grounds):
    """(layout key, the page's frames left to paint once its layout's ground is taken away)."""
    found = page['frames']
    if page['kind'] != 'full':
        return 'content', found
    for key in ('dark', 'photo'):
        ground = grounds[key]
        if found[: len(ground)] == ground:
            return key, found[len(ground) :]
    return 'plain', found


def _drop(holder):
    holder._element.getparent().remove(holder._element)


def _slide(prs, layouts, page, grounds, shared_chrome, pictures):
    key, own = layout_of(page, grounds)
    slide = prs.slides.add_slide(layouts[key])
    titled = False
    if key == 'content':
        title, number, shared = chrome_parts(page)
        if title is not None:
            text.content_title(slide, title)
            titled = True
        for it in shared:
            if it not in shared_chrome:  # never so today: every content page wears the same chrome
                frames.paint(slide, it, pictures)
        if number is not None:
            text.number_box(slide, number)
    for it in own:
        if it['t'] == 'text' and it.get('title') and not titled and key != 'content':
            text.page_title(slide, it)
            titled = True
        else:
            frames.paint(slide, it, pictures)
    if not titled and slide.shapes.title is not None:
        _drop(slide.shapes.title)
    if page['notes']:
        slide.notes_slide.notes_text_frame.text = '\n\n'.join(page['notes'])
    return slide


def draw(pages, title='', sources=None):
    """The .pptx's bytes, one slide a recorded page. `sources`: {image src: bytes} for the pictures not bundled."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = emu(tokens.PAGE_W), emu(tokens.PAGE_H)
    prs.core_properties.title = title
    # The library's own template names its author in both of these.
    prs.core_properties.author = ''
    prs.core_properties.last_modified_by = ''
    pictures = shapes.Pictures(sources)
    colours = _colours(pages)
    grounds = _grounds(colours)
    content = next((page for page in pages if page['kind'] != 'full'), None)
    shared_chrome = chrome_parts(content)[2] if content else []
    layouts = master.dress(prs, colours, shared_chrome, grounds, pictures)
    for page in pages:
        _slide(prs, layouts, page, grounds, shared_chrome, pictures)
    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()
