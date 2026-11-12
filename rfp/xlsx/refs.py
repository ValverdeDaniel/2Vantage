"""Cell references and text escaping for the XML patcher (old `xlsx_fill.py` 891f1b3). Pure."""

import re


class FillError(Exception):
    """The template is not shaped the way the caller believes (a moved header, a missing sheet): the build fails and
    the tests catch it (K71, K96)."""


def col_index(letters):
    """'A' -> 1, 'AA' -> 27."""
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def col_letters(index):
    out = ''
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def split_ref(ref):
    match = re.fullmatch(r'([A-Z]+)(\d+)', ref)
    if not match:
        raise FillError(f'Not a cell reference: {ref!r}')
    return match.group(1), int(match.group(2))


def expand_range(ref):
    """'A5:X6' -> every cell ref inside it, row by row."""
    if ':' not in ref:
        return [ref]
    start, end = ref.split(':', 1)
    c1, r1 = split_ref(start)
    c2, r2 = split_ref(end)
    first, last = sorted((col_index(c1), col_index(c2)))
    return [f'{col_letters(c)}{r}' for r in range(min(r1, r2), max(r1, r2) + 1) for c in range(first, last + 1)]


def escape(text):
    """Strip the control characters XML forbids outright, then escape."""
    text = ''.join(ch for ch in text if ch in '\t\n\r' or ord(ch) >= 0x20)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def unescape(text):
    return (
        text.replace('&amp;', '&')
        .replace('&lt;', '<')
        .replace('&gt;', '>')
        .replace('&quot;', '"')
        .replace('&apos;', "'")
    )
