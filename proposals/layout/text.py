"""The one measure of words on a page (plan.md §9.5; J122, J140, J142). Pure.

Text is held as runs ({text, bold, italic, size, color, link}), never as markup, so nothing a producer or a carrier
typed is ever interpreted ("R&D <b>" prints as those characters; J.5 B14 retires the old Paragraph internals). Lines
break at spaces, greedily, with Helvetica's metrics through reportlab's public `stringWidth`; Arial has the same
metrics, so the PowerPoint wraps where this did. A typed line break starts a new line. A word wider than the box
breaks inside itself, so a long code never overruns its cell.

`paragraph(runs, width, ...)` gives a measured paragraph: {runs, size, leading, align, lines, h}, each line a list of
segments {text, font, size, color, link, w}. The painters draw the lines; the PowerPoint replays the runs in the same
box (slice 31) and a test checks it wraps to the same lines.
"""

from reportlab.pdfbase.pdfmetrics import stringWidth

from . import tokens


def font_of(bold=False, italic=False):
    fonts = tokens.FONTS
    return fonts['bold'] if bold else fonts['italic'] if italic else fonts['regular']


def run(text, size, color, bold=False, italic=False, link=None):
    return {'text': str(text or ''), 'size': size, 'color': color, 'bold': bold, 'italic': italic, 'link': link}


def width(text, size, bold=False, italic=False):
    return stringWidth(text, font_of(bold, italic), size)


def _segment(text, item):
    font = font_of(item['bold'], item['italic'])
    return {
        'text': text,
        'font': font,
        'size': item['size'],
        'color': item['color'],
        'link': item['link'],
        'w': stringWidth(text, font, item['size']),
    }


def _broken(word, item, room):
    """A word wider than the box, cut into pieces that each fit (at least one character a piece)."""
    font, size = font_of(item['bold'], item['italic']), item['size']
    pieces, piece = [], ''
    for char in word:
        if piece and stringWidth(piece + char, font, size) > room:
            pieces.append(piece)
            piece = char
        else:
            piece += char
    return [*pieces, piece] if piece else pieces


def _tokens(runs):
    """[(kind, text, run)]: words, spaces and line breaks, each with the run it belongs to."""
    out = []
    for item in runs:
        for number, part in enumerate(item['text'].split('\n')):
            if number:
                out.append(('break', '', item))
            word = ''
            for char in part:
                if char == ' ':
                    if word:
                        out.append(('word', word, item))
                        word = ''
                    out.append(('space', ' ', item))
                else:
                    word += char
            if word:
                out.append(('word', word, item))
    return out


def _merge(line):
    """Neighbouring segments of one style become one, and the line's trailing spaces go."""
    while line and not line[-1]['text'].strip():
        line.pop()
    out = []
    for seg in line:
        last = out[-1] if out else None
        if last and all(last[key] == seg[key] for key in ('font', 'size', 'color', 'link')):
            last['text'] += seg['text']
            last['w'] += seg['w']
        else:
            out.append(dict(seg))
    if out:
        out[-1]['text'] = out[-1]['text'].rstrip(' ')
        out[-1]['w'] = stringWidth(out[-1]['text'], out[-1]['font'], out[-1]['size'])
    return out


def lines_of(runs, room):
    """The runs broken into lines no wider than `room`."""
    lines, line, used = [], [], 0.0
    for kind, text, item in _tokens(runs):
        if kind == 'break':
            lines.append(_merge(line))
            line, used = [], 0.0
            continue
        if kind == 'space':
            if line:
                seg = _segment(text, item)
                line.append(seg)
                used += seg['w']
            continue
        seg = _segment(text, item)
        if used + seg['w'] <= room + 0.01 or not line:
            if seg['w'] > room + 0.01 and not line:
                pieces = _broken(text, item, room)
                for piece in pieces[:-1]:
                    lines.append(_merge([_segment(piece, item)]))
                seg = _segment(pieces[-1], item)
            line.append(seg)
            used += seg['w']
            continue
        lines.append(_merge(line))
        line, used = [], 0.0
        if seg['w'] > room + 0.01:
            pieces = _broken(text, item, room)
            for piece in pieces[:-1]:
                lines.append(_merge([_segment(piece, item)]))
            seg = _segment(pieces[-1], item)
        line.append(seg)
        used = seg['w']
    lines.append(_merge(line))
    return lines


def paragraph(runs, room, leading=None, align='l', wrap=True):
    """A measured paragraph. `leading` defaults to 1.2 × the largest run's size; `wrap` False keeps one line."""
    runs = [item for item in runs if item['text'] != ''] or runs[:1]
    size = max((item['size'] for item in runs), default=10)
    leading = leading or round(size * 1.2, 2)
    lines = lines_of(runs, room if wrap else 10**9)
    return {
        'runs': [dict(item) for item in runs],
        'size': size,
        'leading': leading,
        'align': align,
        'lines': lines,
        'h': max(1, len(lines)) * leading,
    }


def line_width(line):
    return sum(seg['w'] for seg in line)
