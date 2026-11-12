"""How the locator and the viewer agree on text (E81; the old docscan/locate.py `fold`). Pure.

Matching is loose about form and strict about substance: both sides are folded the same way (NFKC, every dash and the
minus sign as "-", curly quotes straight, whitespace collapsed, lower case; the browser's pdfFind.js folds the same
sets), and a number matches a number ("$1,500.00" is 1500) rather than a string.
"""

import re
import unicodedata

# Every hyphen, dash and the minus sign read as "-"; curly quotes as straight ones. Code points, so no invisible
# character sits in the source.
DASH_CODES = (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212)
QUOTE_CODES = (0x2018, 0x2019, 0x201A, 0x201B, 0x2032)
DQUOTE_CODES = (0x201C, 0x201D, 0x201E, 0x201F, 0x2033)
_FOLD = str.maketrans(
    {
        **{code: '-' for code in DASH_CODES},
        **{code: "'" for code in QUOTE_CODES},
        **{code: '"' for code in DQUOTE_CODES},
    }
)
_SPACE = re.compile(r'\s+')

# A printed figure: "$1,500.00", "1500", "80%", "$ 25". Not glued to a word ("PPO1500" is a code, matched as one) or to
# a decimal point or comma.
NUMBER_TOKEN = re.compile(r'(?<![\w.,])\$?\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s?%?')
# A whole value that is one figure.
_WHOLE_NUMBER = re.compile(r'^\(?-?\$?\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s?%?\)?$')
# A figure this small is printed all over a rate page (copays, percentages): it counts as found only with a plan or
# label word on its own line.
COMMON_MAX = 100


def fold(text):
    """Text as both extractors would agree on it."""
    folded = unicodedata.normalize('NFKC', str(text or '')).translate(_FOLD).lower()
    return _SPACE.sub(' ', folded).strip()


def compact(text):
    """Letters and digits only: how a plan code is compared ("PD 5500-2027" and "PD55002027" are one code)."""
    return re.sub(r'[^a-z0-9]', '', fold(text))


def canonical(digits, fraction=''):
    """A figure as one string: no "$", no thousands commas, no trailing zero in the fraction ("1,500.00" -> "1500",
    "512.50" -> "512.5")."""
    whole = (digits or '').replace(',', '').lstrip('0') or '0'
    frac = (fraction or '').lstrip('.').rstrip('0')
    return f'{whole}.{frac}' if frac else whole


def as_number(value):
    """The canonical figure a value IS, or None when it is not one figure."""
    match = _WHOLE_NUMBER.match(fold(value))
    if not match:
        return None
    return canonical(match.group(1), match.group(2) or '')


def figures_in(text):
    """Every canonical figure printed in (already folded) text, in order."""
    return [canonical(match.group(1), match.group(2) or '') for match in NUMBER_TOKEN.finditer(text)]


def is_common(figure):
    """A small whole figure (20, 80, 100): too common to trust on its own."""
    if figure is None or '.' in figure:
        return False
    return int(figure) <= COMMON_MAX


def as_float(figure):
    try:
        return float(figure)
    except (TypeError, ValueError):
        return None


def words(text):
    """The words of three letters or more, folded: what anchors a common figure to its row."""
    return {word for word in re.findall(r'[a-z0-9]+', fold(text)) if len(word) >= 3}
