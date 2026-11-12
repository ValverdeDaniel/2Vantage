"""The client PowerPoints compared (Q.5): the layouts and the master; per slide its layout, its shapes (each box
±0.5 pt, its shadow), every paragraph's text and every run's font (name, size, bold, italic, colour, kerning), its
tables' cells, its charts (type, categories, series and their values) and its speaker notes.

Slides are lined up by their title, shapes by their kind and text, so a slide or a text box one deck adds is one
difference. Text is masked line by line (`mask.line`). Positions that differ are counted per slide, not one by one.

`compare(old_path, new_path)` → [{where, kind, old, new}].
"""

import difflib

from pptx import Presentation

from . import align, mask

BOX_TOLERANCE = 0.5  # points
NUMBER_TOP = 500  # points from the top below which a box holding only digits is the slide number
_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
_P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'


def _pt(value):
    return None if value is None else round(value / 12700, 2)


def _shadow(shape):
    element = shape._element
    effect_list = element.find(f'.//{_A}effectLst')
    ref = element.find(f'{_P}style/{_A}effectRef')
    return ('effectLst' if effect_list is not None else '-', ref.get('idx') if ref is not None else '-')


def _run_font(run):
    font = run.font
    rpr = run._r.find(f'{_A}rPr')
    colour = None
    try:
        colour = str(font.color.rgb) if font.color and font.color.type is not None else None
    except AttributeError:
        colour = None
    return (font.name, font.size and font.size.pt, font.bold, font.italic, colour,
            rpr.get('kern') if rpr is not None else None)  # fmt: skip


def _paragraphs(shape):
    """[(masked text, (run fonts))] of a text shape or a table, in order."""
    frames = []
    if shape.has_text_frame:
        frames.append(shape.text_frame)
    if getattr(shape, 'has_table', False) and shape.has_table:
        for row in shape.table.rows:
            frames.extend(cell.text_frame for cell in row.cells)
    out = []
    for frame in frames:
        for para in frame.paragraphs:
            text = mask.line(''.join(run.text for run in para.runs))
            if text:
                out.append((text, tuple(_run_font(run) for run in para.runs if run.text.strip())))
    return out


def _chart(shape):
    if not getattr(shape, 'has_chart', False) or not shape.has_chart:
        return None
    chart = shape.chart
    plot = chart.plots[0] if len(chart.plots) else None
    series = tuple((s.name, tuple(s.values)) for s in plot.series) if plot is not None else ()
    return (str(chart.chart_type), tuple(plot.categories) if plot is not None else (), series)


def _without_stamps(shapes):
    """The shapes less the Draft mark (Q.5 masks it): a text box whose words are only a stamp, and the plain shape
    under it (the badge's rounded box)."""
    stamps = [s['box'] for s in shapes if s['raw'] and not s['text'] and None not in s['box']]

    def under(box):
        if None in box:
            return False
        return any(box[0] <= x + w / 2 <= box[0] + box[2] and box[1] <= y + h / 2 <= box[1] + box[3]
                   for x, y, w, h in stamps)  # fmt: skip

    return [s for s in shapes if not (s['raw'] and not s['text']) and not (not s['raw'] and under(s['box']))]


def _shapes(slide):
    out = []
    for shape in slide.shapes:
        raw = shape.text_frame.text.strip() if shape.has_text_frame else ''
        text = mask.line(raw)
        if raw.isdigit() and (_pt(shape.top) or 0) > NUMBER_TOP:
            text = '<page>'  # the slide number: a slide one deck adds renumbers the rest (the alignment says so once)
        out.append({
            'raw': raw,
            'text': text,
            'key': f'{shape.shape_type}|{text[:60]}',
            'box': (_pt(shape.left), _pt(shape.top), _pt(shape.width), _pt(shape.height)),
            'shadow': _shadow(shape),
            'paragraphs': _paragraphs(shape),
            'chart': _chart(shape),
        })  # fmt: skip
    return _without_stamps(out)


def _pairs(old_shapes, new_shapes):
    """Shapes paired by kind and text, in order within each key, whatever order the slide stacks them in."""
    waiting = {}
    for index, shape in enumerate(new_shapes):
        waiting.setdefault(shape['key'], []).append(index)
    pairs, used = [], set()
    for index, shape in enumerate(old_shapes):
        found = waiting.get(shape['key'])
        if found:
            other = found.pop(0)
            used.add(other)
            pairs.append((index, other))
        else:
            pairs.append((index, None))
    pairs.extend((None, index) for index in range(len(new_shapes)) if index not in used)
    return pairs


def _title(slide):
    title = slide.shapes.title
    text = mask.line(title.text_frame.text) if title is not None and title.has_text_frame else ''
    if not text:
        for shape in slide.shapes:
            if shape.has_text_frame and mask.line(shape.text_frame.text):
                text = mask.line(shape.text_frame.text)
                break
    return text[:80] or '(no text)'


def _notes(slide):
    return mask.line(slide.notes_slide.notes_text_frame.text) if slide.has_notes_slide else ''


def _slide_differences(where, old, new):
    out = []
    if old.slide_layout.name != new.slide_layout.name:
        out.append((where, 'layout', old.slide_layout.name, new.slide_layout.name))
    old_shapes, new_shapes = _shapes(old), _shapes(new)
    old_paras = [p for s in old_shapes for p in s['paragraphs']]
    new_paras = [p for s in new_shapes for p in s['paragraphs']]
    matcher = difflib.SequenceMatcher(a=[p[0] for p in old_paras], b=[p[0] for p in new_paras], autojunk=False)
    fonts = {}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            before = ' / '.join(p[0] for p in old_paras[i1:i2]) or None
            after = ' / '.join(p[0] for p in new_paras[j1:j2]) or None
            out.append((where, 'text', before, after))
            continue
        for a, b in zip(old_paras[i1:i2], new_paras[j1:j2], strict=True):
            for x, y in zip(a[1], b[1], strict=False):
                for field, u, v in zip(('font', 'size', 'bold', 'italic', 'colour', 'kern'), x, y, strict=True):
                    if u != v:
                        fonts[(field, u, v)] = fonts.get((field, u, v), 0) + 1
    for (field, u, v), count in sorted(fonts.items(), key=str):
        out.append((where, 'run-font', f'{field} {u!r}', f'{field} {v!r} on {count} runs'))
    shadows, added, removed = set(), [], []
    for o, n in _pairs(old_shapes, new_shapes):
        if n is None:
            removed.append(old_shapes[o]['key'])
            continue
        if o is None:
            added.append(new_shapes[n]['key'])
            continue
        a, b = old_shapes[o], new_shapes[n]
        if None not in a['box'] and None not in b['box']:
            deltas = [round(y - x, 2) for x, y in zip(a['box'], b['box'], strict=True)]
            if max(abs(d) for d in deltas) > BOX_TOLERANCE:
                moved = ' '.join(f'{name}{d:+g}' for name, d in zip(('x', 'y', 'w', 'h'), deltas, strict=True) if d)
                out.append((where, 'shape-position', a['key'][:60], f'{moved} (box {b["box"]})'))
        if a['shadow'] != b['shadow']:
            shadows.add((a['shadow'], b['shadow']))
        if a['chart'] != b['chart']:
            out.append((where, 'chart', a['chart'], b['chart']))
    if removed:
        out.append((where, 'shapes-removed', ' ; '.join(removed), None))
    if added:
        out.append((where, 'shapes-added', None, ' ; '.join(added)))
    for before, after in sorted(shadows):
        out.append((where, 'shadow', before, after))
    if _notes(old) != _notes(new):
        out.append((where, 'notes', _notes(old) or None, _notes(new) or None))
    return out


def _deck(old, new):
    out = []
    old_layouts = [layout.name for layout in old.slide_layouts]
    new_layouts = [layout.name for layout in new.slide_layouts]
    if old_layouts != new_layouts:
        out.append(('layouts', 'layouts', old_layouts, new_layouts))
    old_master = [f'{s.shape_type}|{s.name}' for s in old.slide_master.shapes]
    new_master = [f'{s.shape_type}|{s.name}' for s in new.slide_master.shapes]
    if old_master != new_master:
        out.append(('master', 'master', old_master, new_master))
    if (old.slide_width, old.slide_height) != (new.slide_width, new.slide_height):
        out.append(('slide size', 'slide-size', (_pt(old.slide_width), _pt(old.slide_height)),
                    (_pt(new.slide_width), _pt(new.slide_height))))  # fmt: skip
    return out


def compare(old_path, new_path):
    old, new = Presentation(str(old_path)), Presentation(str(new_path))
    found = _deck(old, new)
    old_slides, new_slides = list(old.slides), list(new.slides)
    if len(old_slides) != len(new_slides):
        found.append(('slides', 'slide-count', len(old_slides), len(new_slides)))
    old_titles, new_titles = [_title(s) for s in old_slides], [_title(s) for s in new_slides]
    for o, n in align.pairs(old_titles, new_titles):
        if n is None:
            found.append((f'old slide {o + 1}', 'slide-removed', old_titles[o], None))
        elif o is None:
            found.append((f'slide {n + 1}', 'slide-added', None, new_titles[n]))
        else:
            found.extend(_slide_differences(f'slide {n + 1} «{new_titles[n]}»', old_slides[o], new_slides[n]))
    return [{'where': w, 'kind': k, 'old': a, 'new': b} for w, k, a, b in found]
