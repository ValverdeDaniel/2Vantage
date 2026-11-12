"""The Fidelity lane (plan.md §12.7; Part Q, Q.2, Q.5, Q.9): old Vantage's client files against 2Vantage's.

    python tools/parity/files.py --deals all            from the repository root, on the host (Git Bash or any shell)
    python tools/parity/files.py --deals GD1,GD2 --out <folder>
    python tools/parity/files.py --fetched <folder>     compare files fetched before (skips the download)
    python files.py --compare <folder>                  the second half alone, inside the parity tools image

1. On the host, with the standard library only (`fidelity/fetch.py`): sign in to both apps and download each golden
   deal's client spreadsheet, PDF, PowerPoint and Paper, the Letter PDF (old `presentation-workbook/`,
   `proposal-pdf/`, `proposal-deck/`, `proposal-paper/`; new `proposal/files/{xlsx,pdf,pptx,letter}/`) into
   %LOCALAPPDATA%/2vantage-fidelity/<time>/<GDn>/ (FIDELITY_OUT or --out overrides).
2. In the parity tools image (no network; the repository read-only at /work; the folder at /data): compare each
   pair (`fidelity/xlsx.py`, `pdf.py` for the PDF and Paper, `pptx.py`) with dates, version and Draft stamps, ids
   and authors masked on both sides (`mask.py`), within Q.5's tolerances; label each difference `intended.yaml` lists
   (`intended.py`); write report.md and differences.json beside the files (`report.py`).

Exit 0 when every difference is a match, within tolerance or intended; 1 when any is unexplained; 2 on a bad setup.
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SPECS = ROOT / 'golden' / 'specs'


def _specs(wanted):
    found = []
    for path in sorted(SPECS.glob('gd*.json')):
        spec = json.loads(path.read_text(encoding='utf-8'))
        key = spec.get('key') or path.stem.upper()
        client = spec['client'] if isinstance(spec['client'], str) else spec['client']['name']
        if wanted == 'all' or key in wanted:
            found.append((key, client))
    return found


def _out(given):
    if given:
        return Path(given)
    base = os.environ.get('FIDELITY_OUT') or Path(os.environ.get('LOCALAPPDATA') or Path.home()) / '2vantage-fidelity'
    return Path(base) / datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')


def _in_tools_image(folder):
    """Run the comparison in the parity tools image, the folder mounted at /data."""
    mount = str(Path(folder).resolve())
    if shutil.which('cygpath') and mount.startswith('/'):
        mount = subprocess.run(['cygpath', '-w', mount], capture_output=True, text=True, check=True).stdout.strip()
    command = [
        'docker', 'compose', '-p', 'vantage-parity', '-f', str(HERE / 'docker-compose.yml'), '--profile', 'tools',
        'run', '--rm', '-v', f'{mount}:/data', 'tools', 'python', '/work/tools/parity/files.py', '--compare', '/data',
    ]  # fmt: skip
    env = {**os.environ, 'MSYS_NO_PATHCONV': '1'}
    return subprocess.run(command, cwd=ROOT, env=env).returncode


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--deals', default='all', help='all, or golden keys such as GD1,GD2')
    parser.add_argument('--out', help='where the files and the report go')
    parser.add_argument('--fetched', help='compare a folder fetched before')
    parser.add_argument('--compare', help='compare a fetched folder here (inside the tools image)')
    args = parser.parse_args(argv)
    if args.compare:
        from fidelity import run

        return run.compare(Path(args.compare), HERE / 'intended.yaml')
    folder = Path(args.fetched) if args.fetched else _out(args.out)
    if not args.fetched:
        from fidelity import fetch

        wanted = 'all' if args.deals == 'all' else {key.strip().upper() for key in args.deals.split(',')}
        specs = _specs(wanted)
        if not specs:
            print(f'No golden spec matches {args.deals}', file=sys.stderr)
            return 2
        folder.mkdir(parents=True, exist_ok=True)
        fetch.fetch(specs, folder)
    print(f'Comparing in the parity tools image: {folder}', flush=True)
    return _in_tools_image(folder)


if __name__ == '__main__':
    sys.path.insert(0, str(HERE))
    sys.exit(main())
