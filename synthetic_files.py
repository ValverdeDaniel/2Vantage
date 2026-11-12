"""Synthetic files for tests and the golden seed (plan.md §12.1, §13.4): small, deterministic, made by code, never a
real file. A root module like gd_big.py: app tests and golden both use it, and no app imports it.

`pdf(pages)` writes a minimal PDF with a real text layer (standard Helvetica, WinAnsi), so pypdf and pdf.js both
read its words; each page is a list of lines `(x, y, text)` or `(x, y, text, size)` in points from the bottom left,
or `('rect', x, y, w, h)` for a ruled box. `png()` is a one-pixel image.
"""

import struct
import zlib

PAGE = (612, 792)  # US Letter


def _escape(text):
    return str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _content(lines):
    ops = []
    for line in lines:
        if line[0] == 'rect':
            _, x, y, w, h = line
            ops.append(f'0.6 G 0.5 w {x} {y} {w} {h} re S')
            continue
        x, y, text, *rest = line
        size = rest[0] if rest else 10
        font = '/F2' if len(rest) > 1 and rest[1] else '/F1'
        ops.append(f'BT {font} {size} Tf {x} {y} Td ({_escape(text)}) Tj ET')
    return '\n'.join(ops).encode('latin-1')


def pdf(pages, size=PAGE):
    """A PDF whose pages carry the given lines (see the module doc). Returns bytes."""
    objects = []

    def add(body):
        objects.append(body)
        return len(objects)

    catalog = add(None)
    page_tree = add(None)
    font = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    bold = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
    kids = []
    for lines in pages:
        stream = _content(lines)
        content = add(b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream')
        kids.append(
            add(
                (
                    f'<< /Type /Page /Parent {page_tree} 0 R /MediaBox [0 0 {size[0]} {size[1]}] '
                    f'/Resources << /Font << /F1 {font} 0 R /F2 {bold} 0 R >> >> /Contents {content} 0 R >>'
                ).encode()
            )
        )
    objects[catalog - 1] = f'<< /Type /Catalog /Pages {page_tree} 0 R >>'.encode()
    refs = ' '.join(f'{kid} 0 R' for kid in kids)
    objects[page_tree - 1] = f'<< /Type /Pages /Kids [{refs}] /Count {len(kids)} >>'.encode()
    out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f'{number} 0 obj\n'.encode() + body + b'\nendobj\n'
    xref = len(out)
    out += f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode()
    out += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets)
    out += f'trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
    return bytes(out)


def text_pdf(*pages):
    """A PDF from plain text pages: each page a list of strings, one line each from the top."""
    return pdf([[(72, 720 - 16 * i, text) for i, text in enumerate(page)] for page in pages])


def png():
    """A one-pixel white PNG."""

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'))
