"""Line two sequences up the way a reader would (difflib over their labels), so one inserted row or slide reads as
one difference rather than shifting everything after it.

`pairs(old_keys, new_keys)` → [(old index | None, new index | None)] in order: equal and same-sized replaced runs pair
up one by one; the rest are one-sided. The workbook aligns rows by their label (column A, else B) and columns by
their heading cells; the PDF and the deck align pages and slides by their titles.
"""

import difflib


def pairs(old_keys, new_keys):
    matcher = difflib.SequenceMatcher(a=old_keys, b=new_keys, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
            out.extend(zip(range(i1, i2), range(j1, j2), strict=True))
            continue
        if tag == 'replace':
            # Unequal runs: pair the front, the rest one-sided.
            common = min(i2 - i1, j2 - j1)
            out.extend(zip(range(i1, i1 + common), range(j1, j1 + common), strict=True))
            i1, j1 = i1 + common, j1 + common
        out.extend((i, None) for i in range(i1, i2))
        out.extend((None, j) for j in range(j1, j2))
    return out


def mapping(found):
    """{old index: new index} for the paired entries of `pairs`."""
    return {old: new for old, new in found if old is not None and new is not None}
