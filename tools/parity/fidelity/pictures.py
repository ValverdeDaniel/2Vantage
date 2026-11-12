"""Page pictures (Q.5): a PDF rasterized at 110 DPI with poppler, and the share of pixels two pictures disagree on.
A pixel differs when any channel moves by more than CHANNEL_STEP, so anti-aliasing noise is not a difference; two
pictures of different sizes differ everywhere. What the words leave masked (`pdf._masked_boxes`: a stamp, a date) is
left out of the pictures too, on both sides, so a Draft mark one file has is no difference here either.
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

DPI = 110
PIXEL_TOLERANCE = 0.0005  # 0.05% of a page's pixels
CHANNEL_STEP = 32


def rasterize(pdf, folder, tag):
    """[png path] one per page, in order."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    prefix = folder / tag
    subprocess.run(['pdftoppm', '-r', str(DPI), '-png', str(pdf), str(prefix)], check=True)
    return sorted(folder.glob(f'{tag}-*.png'), key=lambda path: int(path.stem.rsplit('-', 1)[1]))


def _hidden(picture, boxes):
    """`picture` with each box (x0, y0, x1, y1 in points from the top-left) painted over."""
    picture = picture.convert('RGB')
    scale = DPI / 72
    draw = ImageDraw.Draw(picture)
    for x0, y0, x1, y1 in boxes:
        draw.rectangle([x0 * scale, y0 * scale, x1 * scale, y1 * scale], fill=(255, 0, 255))
    return picture


def differing_share(old_png, new_png, hidden=()):
    """The share of pixels that differ, the `hidden` boxes (points) left out of both pictures."""
    with Image.open(old_png) as a, Image.open(new_png) as b:
        if a.size != b.size:
            return 1.0
        diff = ImageChops.difference(_hidden(a, hidden), _hidden(b, hidden)).convert('L')
        changed = sum(diff.point(lambda value: 255 if value > CHANNEL_STEP else 0).histogram()[255:])
        return changed / (a.size[0] * a.size[1])
