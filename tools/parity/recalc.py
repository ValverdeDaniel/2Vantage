"""The Recalc lane (plan.md §9.4, §12.1, §12.6; Part Q, Q.2): LibreOffice recalculates each workbook and every formula's
result must equal the result the app stored in it.

    python recalc.py <folder>          every .xlsx in the folder; exit 1 on any mismatch

Runs in the parity tools image (headless LibreOffice, openpyxl; no network; stdlib otherwise). For each file: a copy
with every formula's cached value stripped (so LibreOffice must calculate, whatever its load setting), converted with
`soffice --headless --convert-to xlsx` under a throw-away profile set to always recalculate; then each formula cell's
stored result (openpyxl, data_only) is compared with LibreOffice's: numbers within 1e-9, '' and None both blank, text
exactly. A file with no formula compared fails too. The pytest (`pytest -m recalc`) imports `recalc_dir` by path.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import openpyxl

TOLERANCE = 1e-9
PROFILE = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse">
<value>0</value></prop></item>
<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="ODFRecalcMode" oor:op="fuse">
<value>0</value></prop></item>
</oor:items>
"""
# A formula cell as XlsxWriter writes it: <c r="A1" s="3" t="str"><f>…</f><v>…</v></c>.
_CACHED = re.compile(r'<c\b([^>]*)>(<f>.*?</f>|<f\b[^>]*/>)<v>.*?</v></c>', re.S)
_TYPE = re.compile(r'\st="[^"]*"')


def _uncached(match):
    return f'<c{_TYPE.sub("", match.group(1))}>{match.group(2)}</c>'


def strip_results(source, target):
    """A copy of the workbook with no formula result cached: LibreOffice must work each one out."""
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as new:
        for item in old.infolist():
            data = old.read(item.filename)
            if item.filename.startswith('xl/worksheets/sheet') and item.filename.endswith('.xml'):
                data = _CACHED.sub(_uncached, data.decode('utf-8')).encode('utf-8')
            new.writestr(item, data)


def _profile(folder):
    user = os.path.join(folder, 'user')
    os.makedirs(user, exist_ok=True)
    with open(os.path.join(user, 'registrymodifications.xcu'), 'w', encoding='utf-8') as handle:
        handle.write(PROFILE)
    return 'file://' + folder


def convert(paths, out, soffice='soffice'):
    """LibreOffice opens each file (recalculating everything) and saves it as .xlsx into `out`."""
    profile = tempfile.mkdtemp(prefix='lo-profile-')
    try:
        command = [
            soffice,
            f'-env:UserInstallation={_profile(profile)}',
            '--headless',
            '--norestore',
            '--nologo',
            '--calc',
            '--convert-to',
            'xlsx',
            '--outdir',
            out,
            *paths,
        ]
        subprocess.run(command, check=True, capture_output=True, timeout=600)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _blank(value):
    return value is None or value == ''


def same(a, b):
    if _blank(a) or _blank(b):
        return _blank(a) and _blank(b)
    if (
        isinstance(a, int | float)
        and isinstance(b, int | float)
        and not isinstance(a, bool)
        and not isinstance(b, bool)
    ):
        return abs(float(a) - float(b)) <= TOLERANCE
    return a == b


def formula_cells(path):
    """{(sheet, coordinate): stored result} for every formula cell."""
    formulas = openpyxl.load_workbook(path, data_only=False)
    stored = openpyxl.load_workbook(path, data_only=True)
    out = {}
    for sheet in formulas.worksheets:
        values = stored[sheet.title]
        for row in sheet.iter_rows():
            for cell in row:
                if cell.data_type == 'f' or (isinstance(cell.value, str) and cell.value.startswith('=')):
                    out[(sheet.title, cell.coordinate)] = values[cell.coordinate].value
    return out


def compare(original, recalculated):
    """[(sheet, cell, stored, LibreOffice)] where they differ, and how many formula cells were compared."""
    stored = formula_cells(original)
    found = openpyxl.load_workbook(recalculated, data_only=True)
    mismatches = []
    for (title, coordinate), value in sorted(stored.items()):
        other = found[title][coordinate].value if title in found.sheetnames else '<missing sheet>'
        if not same(value, other):
            mismatches.append((title, coordinate, value, other))
    return mismatches, len(stored)


def recalc_dir(folder, soffice='soffice', report=print):
    """{file name: [mismatch text]} for every .xlsx in `folder`; an empty list is a pass."""
    names = sorted(name for name in os.listdir(folder) if name.lower().endswith('.xlsx'))
    if not names:
        return {'(none)': ['no .xlsx file in ' + folder]}
    work = tempfile.mkdtemp(prefix='recalc-')
    try:
        stripped, out = os.path.join(work, 'in'), os.path.join(work, 'out')
        os.makedirs(stripped)
        os.makedirs(out)
        for name in names:
            strip_results(os.path.join(folder, name), os.path.join(stripped, name))
        convert([os.path.join(stripped, name) for name in names], out, soffice)
        results = {}
        for name in names:
            recalculated = os.path.join(out, name)
            if not os.path.exists(recalculated):
                results[name] = ['LibreOffice wrote no file']
                continue
            mismatches, compared = compare(os.path.join(folder, name), recalculated)
            lines = [f'{t}!{c}: stored {s!r}, LibreOffice {o!r}' for t, c, s, o in mismatches]
            if not compared:
                lines.append('no formula cell compared')
            results[name] = lines
            report(f'{name}: {compared} formula cells, {len(mismatches)} mismatches')
            for line in lines[:50]:
                report('  ' + line)
        return results
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    results = recalc_dir(argv[1])
    failed = [name for name, lines in results.items() if lines]
    print('Recalc:', 'FAIL ' + ', '.join(failed) if failed else f'PASS ({len(results)} files)')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
