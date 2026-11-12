"""The client PowerPoint (plan.md §9.6; J141): `draw(pages, title, sources)` → the .pptx's bytes, replaying the frames
`layout/record.lay_out` recorded, as `paint/pdf.py` draws them. python-pptx 1.0.2, the old app's pin.

`deck` the replay, `master` the slide master and its four layouts, `text`, `shapes`, `table` and `chart` the painters
of each recorded kind (`frames.DRAW`), `units` points, colours and shape defaults.
"""

from .deck import draw

__all__ = ['draw']
