"""Page pictures (Q.5): a PDF rasterized at 110 DPI with poppler, and the share of pixels two pictures disagree on.
A pixel differs when any channel moves by more than CHANNEL_STEP, so anti-aliasing noise is not a difference; two
pictures of different sizes differ everywhere.
"""

import subprocess
from pathlib import Path

from PIL import Image, ImageChops

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


def differing_share(old_png, new_png):
    with Image.open(old_png) as a, Image.open(new_png) as b:
        if a.size != b.size:
            return 1.0
        diff = ImageChops.difference(a.convert('RGB'), b.convert('RGB')).convert('L')
        changed = sum(diff.point(lambda value: 255 if value > CHANNEL_STEP else 0).histogram()[255:])
        return changed / (a.size[0] * a.size[1])
