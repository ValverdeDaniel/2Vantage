"""The workbook package, rewritten the way Excel writes it (old `xlsx_fill.fill_xlsx` 891f1b3; K90).

`fill(src, edits, ...)` patches the named sheets and copies every other zip part through byte for byte (styles.xml,
workbook.xml and core.xml only when asked). The zip mirrors Excel's: entry order, compression method (a STORED logo
stays STORED), the DOS 1980 timestamps, the FAT `create_system`, external attributes 0 and the deflate flag 6, patched
in both the local header and the central directory. `read_sheet` serves the drift guard.
"""

import io
import re
import zipfile

from deals import clock

from . import formulas
from .refs import FillError, escape, expand_range, unescape
from .sheet import XF_RE, Sheet, text_styles


def sheet_parts(src):
    """{sheet name: part path} from the workbook and its rels. Attributes are read one by one: Excel writes Id before
    Target, openpyxl Target first."""
    with zipfile.ZipFile(io.BytesIO(src)) as archive:
        workbook = archive.read('xl/workbook.xml').decode('utf-8')
        rels = archive.read('xl/_rels/workbook.xml.rels').decode('utf-8')
    targets = {}
    for element in re.findall(r'<Relationship\b[^>]*/?>', rels):
        rid = re.search(r'\bId="([^"]+)"', element)
        target = re.search(r'\bTarget="([^"]+)"', element)
        if rid and target:
            targets[rid.group(1)] = target.group(1)
    out = {}
    for sheet in re.findall(r'<sheet\b[^>]*/>', workbook):
        name = re.search(r'name="([^"]*)"', sheet).group(1)
        target = targets.get(re.search(r'r:id="([^"]+)"', sheet).group(1), '')
        out[unescape(name)] = target.lstrip('/') if target.startswith('/') else 'xl/' + target.lstrip('./')
    return out


def read_sheet(src, sheet_name):
    """(Sheet, shared strings): what the drift guard and the tests read a bundled or filled file through."""
    paths = sheet_parts(src)
    if sheet_name not in paths:
        raise FillError(f'No sheet named {sheet_name!r}')
    with zipfile.ZipFile(io.BytesIO(src)) as archive:
        sheet = Sheet(archive.read(paths[sheet_name]).decode('utf-8'))
        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            raw = archive.read('xl/sharedStrings.xml').decode('utf-8')
            for item in re.findall(r'<si>(.*?)</si>', raw, re.S):
                shared.append(unescape(''.join(re.findall(r'<t[^>]*>(.*?)</t>', item, re.S))))
    return sheet, shared


def _add_merges(xml, merges):
    if not merges:
        return xml
    block = re.search(r'<mergeCells count="(\d+)">(.*?)</mergeCells>', xml, re.S)
    added = ''.join(f'<mergeCell ref="{ref}"/>' for ref in merges)
    if block:
        count = int(block.group(1)) + len(merges)
        merged = f'<mergeCells count="{count}">{block.group(2)}{added}</mergeCells>'
        return f'{xml[: block.start()]}{merged}{xml[block.end() :]}'
    return xml.replace('</sheetData>', f'</sheetData><mergeCells count="{len(merges)}">{added}</mergeCells>', 1)


def _clone_styles(styles_xml, clones):
    """Append cloned `<xf>` entries: (xml, {name: new xf id}). Only where a template has no style for what must be
    written (Warner's wrapped Notes cell, slice 46). The alignment goes FIRST inside the xf (alignment → protection →
    extLst; Excel is strict)."""
    if not clones:
        return styles_xml, {}
    block = re.search(r'<cellXfs count="(\d+)">(.*?)</cellXfs>', styles_xml, re.S)
    if not block:
        raise FillError('styles.xml has no cellXfs')
    entries = XF_RE.findall(block.group(2))
    count = int(block.group(1))
    added, ids = [], {}
    for name, (base, alignment) in clones.items():
        if base >= len(entries):
            raise FillError(f'No style {base} to clone for {name}')
        xf = re.sub(r'<alignment[^>]*/>', '', entries[base])
        xf = re.sub(r'<alignment[^>]*>.*?</alignment>', '', xf, flags=re.S)
        if alignment:
            inner = '<alignment ' + ' '.join(f'{k}="{v}"' for k, v in alignment.items()) + '/>'
            if xf.endswith('/>'):
                xf = f'{xf[:-2]}>{inner}</xf>'
            else:
                head_end = xf.index('>') + 1
                xf = f'{xf[:head_end]}{inner}{xf[head_end:]}'
            if 'applyAlignment' not in xf:
                xf = xf.replace('<xf ', '<xf applyAlignment="1" ', 1)
        added.append(xf)
        ids[name] = count + len(added) - 1
    new_block = f'<cellXfs count="{count + len(added)}">{block.group(2)}{"".join(added)}</cellXfs>'
    return styles_xml[: block.start()] + new_block + styles_xml[block.end() :], ids


def _stamp_core(core_xml, modified_by):
    """What Excel writes on save: who last saved it, and when."""
    now = clock.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    who = escape(str(modified_by))
    if '<cp:lastModifiedBy>' in core_xml or '<cp:lastModifiedBy/>' in core_xml:
        core_xml = re.sub(
            r'<cp:lastModifiedBy>.*?</cp:lastModifiedBy>|<cp:lastModifiedBy/>',
            f'<cp:lastModifiedBy>{who}</cp:lastModifiedBy>',
            core_xml,
            count=1,
            flags=re.S,
        )
    else:
        core_xml = core_xml.replace(
            '</cp:coreProperties>', f'<cp:lastModifiedBy>{who}</cp:lastModifiedBy></cp:coreProperties>', 1
        )
    if '<dcterms:modified' in core_xml:
        return re.sub(
            r'<dcterms:modified([^>]*)>.*?</dcterms:modified>',
            rf'<dcterms:modified\1>{now}</dcterms:modified>',
            core_xml,
            count=1,
            flags=re.S,
        )
    return core_xml.replace(
        '</cp:coreProperties>',
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>',
        1,
    )


def _resolve_target(base, target):
    if target.startswith('/'):
        return target.lstrip('/')
    out = []
    for part in (base + target).split('/'):
        if part == '..':
            if out:
                out.pop()
        elif part not in ('', '.'):
            out.append(part)
    return '/'.join(out)


def _drop_parts(payload, names, parts):
    """Remove parts and every relationship or content-type override pointing at them (a workbook saved with "Save
    Thumbnail" off has neither)."""
    dropped = {part for part in parts if part in payload}
    if not dropped:
        return payload, names
    for name in names:
        if name in dropped:
            continue
        if name.endswith('.rels'):
            xml = payload[name].decode('utf-8')
            base = name.split('_rels/')[0]
            for element in re.findall(r'<Relationship\b[^>]*/>', xml):
                target = re.search(r'\bTarget="([^"]+)"', element)
                if target and _resolve_target(base, target.group(1)) in dropped:
                    xml = xml.replace(element, '', 1)
            payload[name] = xml.encode('utf-8')
        elif name == '[Content_Types].xml':
            xml = payload[name].decode('utf-8')
            for element in re.findall(r'<Override\b[^>]*/>', xml):
                part = re.search(r'\bPartName="([^"]+)"', element)
                if part and part.group(1).lstrip('/') in dropped:
                    xml = xml.replace(element, '', 1)
            payload[name] = xml.encode('utf-8')
    for part in dropped:
        del payload[part]
    return payload, [name for name in names if name not in dropped]


def _patch_sheet(original, spec, text_xfs, clone_ids):
    sheet = Sheet(original, text_xfs)
    source_row = spec.get('style_source_row')
    for ref in spec.get('clear') or []:
        for cell in expand_range(ref):
            sheet.write(cell, None)
    explicit = spec.get('styles') or {}
    for ref, value in (spec.get('writes') or {}).items():
        style = explicit.get(ref)
        if isinstance(style, str):  # a cloned style, by name
            style = clone_ids.get(style)
        if isinstance(value, tuple):
            value, style = value
        sheet.write(ref, value, style, style_source_row=source_row)
    for row_num, points in (spec.get('row_heights') or {}).items():
        sheet.set_row_height(int(row_num), points)
    return sheet, _add_merges(sheet.render(), spec.get('merges') or [])


def _set_full_calc(workbook):
    if '<calcPr' in workbook:
        return re.sub(
            r'<calcPr\b[^>]*?/>', lambda m: m.group(0)[:-2].rstrip() + ' fullCalcOnLoad="1"/>', workbook, count=1
        )
    return workbook.replace('</workbook>', '<calcPr fullCalcOnLoad="1"/></workbook>')


def fill(src, edits, *, full_calc_on_load=False, style_clones=None, modified_by=None, drop_parts=None):
    """(bytes, warnings). `edits` is {sheet name: {writes: {ref: value | (value, style)}, clear: [ranges], merges,
    row_heights, style_source_row, styles: {ref: xf}}}. `full_calc_on_load` is True, False or 'auto' (only when a
    formula on a patched sheet reads a written column); `modified_by` stamps docProps/core.xml as a save does;
    `drop_parts` removes package parts with their relationships."""
    paths = sheet_parts(src)
    with zipfile.ZipFile(io.BytesIO(src)) as archive:
        names = archive.namelist()
        payload = {name: archive.read(name) for name in names}
        infos = {info.filename: info for info in archive.infolist()}
    clone_ids = {}
    if style_clones:
        styles_xml, clone_ids = _clone_styles(payload['xl/styles.xml'].decode('utf-8'), style_clones)
        payload['xl/styles.xml'] = styles_xml.encode('utf-8')
    styles = payload.get('xl/styles.xml')
    text_xfs = text_styles(styles.decode('utf-8')) if styles else frozenset()
    warnings, touched = [], False
    for sheet_name, spec in edits.items():
        if sheet_name not in paths:
            raise FillError(f'No sheet named {sheet_name!r}')
        original = payload[paths[sheet_name]].decode('utf-8')
        sheet, xml = _patch_sheet(original, spec, text_xfs, clone_ids)
        payload[paths[sheet_name]] = xml.encode('utf-8')
        warnings += sheet.warnings
        if full_calc_on_load == 'auto' and not touched:
            touched = formulas.touches(original, sheet_name, {col for col, _row in sheet.written})
    if full_calc_on_load is True or (full_calc_on_load == 'auto' and touched):
        payload['xl/workbook.xml'] = _set_full_calc(payload['xl/workbook.xml'].decode('utf-8')).encode('utf-8')
    if modified_by and 'docProps/core.xml' in payload:
        payload['docProps/core.xml'] = _stamp_core(payload['docProps/core.xml'].decode('utf-8'), modified_by).encode()
    if drop_parts:
        payload, names = _drop_parts(payload, names, drop_parts)
    return write_package(payload, names, infos), warnings


def write_package(payload, names, infos):
    """The parts back in the original order and method, with an Excel-saved file's timestamps and create_system."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as out:
        for name in names:
            info = infos[name]
            entry = zipfile.ZipInfo(name, date_time=info.date_time)
            entry.compress_type = info.compress_type  # a STORED original stays STORED, as Excel leaves it
            entry.create_system = 0
            entry.create_version = 45
            entry.extract_version = 20 if info.compress_type else 10
            out.writestr(entry, payload[name])
    return _excel_entry_headers(buffer.getvalue())


def _excel_entry_headers(data):
    """What `zipfile` will not let us set: external attributes 0 and the general-purpose flag 6 (Excel's deflate hint)
    on deflated entries, 0 on stored ones, in both the local header and the central directory."""
    eocd = data.rfind(b'PK\x05\x06')
    if eocd < 0:
        return data
    buf = bytearray(data)
    cd_offset = int.from_bytes(buf[eocd + 16 : eocd + 20], 'little')
    cd_size = int.from_bytes(buf[eocd + 12 : eocd + 16], 'little')
    pos = cd_offset
    while pos < cd_offset + cd_size and buf[pos : pos + 4] == b'PK\x01\x02':
        method = int.from_bytes(buf[pos + 10 : pos + 12], 'little')
        name_len = int.from_bytes(buf[pos + 28 : pos + 30], 'little')
        extra_len = int.from_bytes(buf[pos + 30 : pos + 32], 'little')
        comment_len = int.from_bytes(buf[pos + 32 : pos + 34], 'little')
        local = int.from_bytes(buf[pos + 42 : pos + 46], 'little')
        flag = (6 if method == zipfile.ZIP_DEFLATED else 0).to_bytes(2, 'little')
        buf[pos + 8 : pos + 10] = flag
        buf[pos + 38 : pos + 42] = b'\x00\x00\x00\x00'
        if buf[local : local + 4] == b'PK\x03\x04':
            buf[local + 6 : local + 8] = flag
        pos += 46 + name_len + extra_len + comment_len
    return bytes(buf)
