"""Reading the carrier's XFA template packet (G124). Pure apart from `extract_xfa_streams`, which needs pypdf.

Florida Blue's 51+ questionnaire is a dynamic XFA form: its option lists and its dependent-dropdown cascade live in
the `template` packet — the lists as `<items>` blocks (the SIC table as two parallel ones: codes, and the hidden
`save="1"` descriptions), the cascade as two `change` event scripts whose `switch` statements call `addItem(...)` and
flip `presence = "visible"`. Two traps, both on the Florida Blue form:
1. a `<variables>` block holds `newArray(...)` literals that look like the same lists but are a stale draft: parse the
   `switch` bodies, never the variables;
2. labels are dirty — non-breaking spaces, entities, doubled and trailing spaces — and level-1 and level-2 labels must
   be normalised identically or the join between them silently loses rows.
"""

import hashlib
import html
import re

TEMPLATE_PACKET = 'template'
# A field made visible in a cascade branch turns on a group of answer slots: {driving field: effect flag}.
EFFECT_FIELDS = {
    'txtSurgPlanned': 'surgery',
    'txtTransplantPlanned': 'transplant',
    'numCancerDetailyes': 'cancer_counts',
}
NO_XFA = "This PDF has no XFA form data: use the carrier's original file, not a flattened print."


def norm(text):
    """NBSP to space, entities unescaped, whitespace runs collapsed, stripped — on both sides of every join."""
    if text is None:
        return ''
    return re.sub(r'\s+', ' ', html.unescape(text).replace(' ', ' ')).strip()


def extract_xfa_streams(pdf_bytes):
    """{packet name: bytes} of a dynamic-XFA PDF; ValueError for a PDF with no XFA (a flattened print looks alike)."""
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    acroform = reader.trailer['/Root'].get('/AcroForm')
    xfa = acroform.get('/XFA') if acroform else None
    if not xfa:
        raise ValueError(NO_XFA)
    packets = {}
    for i in range(0, len(xfa) - 1, 2):
        stream = xfa[i + 1]
        if hasattr(stream, 'get_object'):
            packets[str(xfa[i])] = stream.get_object().get_data()
    if TEMPLATE_PACKET not in packets:
        raise ValueError('XFA form has no "template" packet.')
    return packets


def _field_blocks(xml, name):
    """Every <field name="…"> … </field> for `name`, in document order (a form may reuse a name: two `drpSIC`)."""
    return re.findall(rf'<field\s+name="{re.escape(name)}"[\s>].*?</field\s*>', xml, re.S)


def _items_blocks(field_xml):
    """[(attrs, [option, …])] for each <items> block of one field."""
    out = []
    for attrs, body in re.findall(r'<items\b([^>]*)>(.*?)</items\s*>', field_xml, re.S):
        out.append((attrs.strip(), [norm(t) for t in re.findall(r'<text\b[^>]*>(.*?)</text\s*>', body, re.S)]))
    return out


def _caption(field_xml):
    """A field's visible caption: plain `<text>` or rich `<exData>`."""
    found = re.search(r'<caption\b.*?</caption\s*>', field_xml, re.S)
    if not found:
        return ''
    for tag in ('text', 'exData'):
        inner = re.search(rf'<{tag}\b[^>]*>(.*?)</{tag}\s*>', found.group(0), re.S)
        if inner:
            return norm(re.sub(r'<[^>]+>', ' ', inner.group(1)))
    return ''


def _scripts(xml):
    """Every <script> body, unescaped — never the <variables> block (trap 1)."""
    return [html.unescape(m.group(1)) for m in re.finditer(r'<script\b[^>]*>(.*?)</script\s*>', xml, re.S)]


def _switch_cases(source):
    """A JS `switch` as {case label: body}; a fall-through run of labels shares one body."""
    cases, pending, body = {}, [], []

    def flush():
        for label in pending:
            cases[label] = '\n'.join(body)

    for line in source.splitlines():
        found = re.search(r'case\s+"(.*?)"\s*:', line)
        if found:
            if body:
                flush()
                pending.clear()
                body.clear()
            pending.append(norm(found.group(1)))
        elif pending:
            body.append(line)
    flush()
    return cases


def _effects(body):
    return {
        flag: bool(re.search(rf'{re.escape(field)}\.presence\s*=\s*"visible"', body))
        for field, flag in EFFECT_FIELDS.items()
    }


def _preamble_resets(source):
    """The flags a script hides before its `switch`: the ones a condition overrides rather than inherits."""
    head = source.split('switch', 1)[0]
    return sorted(
        flag
        for field, flag in EFFECT_FIELDS.items()
        if re.search(rf'{re.escape(field)}\.presence\s*=\s*"hidden"', head)
    )


def _added_items(body, target):
    return [norm(m) for m in re.findall(re.escape(target) + r'\.addItem\s*\(\s*"(.*?)"\s*\)', body)]


def _subform_block(xml, start):
    """The whole <subform>…</subform> from `start`, honouring nesting and self-closing tags."""
    depth = 0
    for found in re.finditer(r'<(/?)subform\b[^>]*>', xml[start:]):
        if found.group(0).rstrip('>').rstrip().endswith('/'):
            continue
        depth += -1 if found.group(1) else 1
        if depth == 0:
            return xml[start : start + found.end()]
    return xml[start:]


def _category_legend(xml):
    """The static table of category names printed above Section IV (`<draw>` text in unnamed row subforms)."""
    start = xml.find('<subform name="tblCategories"')
    if start == -1:
        return []
    block = _subform_block(xml, start)
    rows = []
    spans = list(re.finditer(r'<subform\s+layout="row"', block))
    for index, found in enumerate(spans):
        end = spans[index + 1].start() if index + 1 < len(spans) else len(block)
        draws = re.finditer(r'<draw\b.*?</draw\s*>', block[found.start() : end], re.S)
        cells = [cell for cell in (norm(re.sub(r'<[^>]+>', ' ', m.group(0))) for m in draws) if cell]
        if cells:
            rows.append(cells)
    return rows


def _sic_codes(xml):
    for field_xml in _field_blocks(xml, 'drpSIC'):
        blocks = _items_blocks(field_xml)
        if len(blocks) != 2:
            continue
        visible = next((o for a, o in blocks if 'save="1"' not in a), None)
        saved = next((o for a, o in blocks if 'save="1"' in a), None)
        if visible and saved and len(visible) == len(saved):
            return list(zip(visible, saved, strict=True))
    raise ValueError('could not pair the drpSIC code and description item lists')


def _captions(xml):
    captions = {}
    for found in re.finditer(r'<field\s+name="([^"]+)"[\s>]', xml):
        name = found.group(1)
        blocks = _field_blocks(xml, name) if name not in captions else []
        caption = _caption(blocks[0]) if blocks else ''
        if caption:
            captions[name] = caption
    return captions


def parse_template(xml_bytes):
    """The template packet as the data module's constants (deterministic, no side effects)."""
    xml = xml_bytes.decode('utf-8')
    category_fields = _field_blocks(xml, 'drpMedCat')
    if not category_fields:
        raise ValueError('template has no drpMedCat field')
    categories = next((options for attrs, options in _items_blocks(category_fields[0]) if 'save="1"' in attrs), [])
    if not categories:
        raise ValueError('drpMedCat has no save="1" items block')
    scripts = _scripts(xml)
    level1 = next((s for s in scripts if 'drpMedCondition.addItem' in s), None)
    level2 = next((s for s in scripts if 'drpMedConDetail.addItem' in s and 'drpMedCondition.addItem' not in s), None)
    if level1 is None or level2 is None:
        raise ValueError('template is missing one of the two cascade scripts')
    level1_cases, level2_cases = _switch_cases(level1), _switch_cases(level2)
    return {
        'MED_CATEGORIES': categories,
        'CONDITIONS_BY_CATEGORY': {label: _added_items(b, 'drpMedCondition') for label, b in level1_cases.items()},
        'DETAILS_BY_CONDITION': {label: _added_items(b, 'drpMedConDetail') for label, b in level2_cases.items()},
        'CATEGORY_EFFECTS': {label: _effects(b) for label, b in level1_cases.items()},
        'CONDITION_EFFECTS': {label: _effects(b) for label, b in level2_cases.items()},
        'CONDITION_OVERRIDES': _preamble_resets(level2),
        'SIC_CODES': _sic_codes(xml),
        'CATEGORY_LEGEND': _category_legend(xml),
        'CAPTIONS': _captions(xml),
        'SOURCE_SHA256': hashlib.sha256(xml_bytes.replace(b'\r\n', b'\n')).hexdigest(),  # as checks.py reads it
    }
