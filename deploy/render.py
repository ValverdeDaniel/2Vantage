"""Fill deploy/cloudrun/*.yaml from deploy/staging.env for one image (deploy/README.md).

    python deploy/render.py --commit <full commit SHA> [--env deploy/staging.env] [--out <folder>]

Each `${NAME}` takes its value from the env file, plus GIT_SHA (the commit) and IMAGE, Artifact Registry's name for
it: <REGION>-docker.pkg.dev/<PROJECT_ID>/<REPOSITORY>/<IMAGE_NAME>:<commit>. A line `# @include <file>` takes that
file's lines, indented as the marker is. A blank or unknown name refuses the whole render, so nothing half-configured
reaches Cloud Run. The rendered files go to a temporary folder outside the repository; it prints their paths.
Standard library only.
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / 'cloudrun'
SHARED = {'app-env.yaml'}  # included, never applied on its own
INCLUDE = re.compile(r'^(?P<indent>\s*)# @include (?P<name>\S+)\s*$')
NAME = re.compile(r'\$\{([A-Z0-9_]+)\}')


def read_env(path):
    values = {}
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep:
            raise SystemExit(f'{path}:{number}: expected NAME=value')
        values[key.strip()] = value.strip()
    return values


def expand(text):
    lines = []
    for line in text.splitlines():
        found = INCLUDE.match(line)
        if not found:
            lines.append(line)
            continue
        for included in (TEMPLATES / found['name']).read_text(encoding='utf-8').splitlines():
            if included.strip() and not included.startswith('#'):
                lines.append(found['indent'] + included)
    return '\n'.join(lines) + '\n'


def render(values):
    """{file name: rendered text}; raises SystemExit naming every blank or unknown value."""
    rendered, missing = {}, set()
    for template in sorted(TEMPLATES.glob('*.yaml')):
        if template.name in SHARED:
            continue
        text = expand(template.read_text(encoding='utf-8'))
        missing |= {name for name in NAME.findall(text) if not values.get(name)}
        rendered[template.name] = NAME.sub(lambda found: values.get(found[1], ''), text)
    if missing:
        raise SystemExit(f'Fill these in deploy/staging.env first: {", ".join(sorted(missing))}')
    return rendered


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--commit', required=True, help='the full commit SHA the image was built from')
    parser.add_argument('--env', default=str(HERE / 'staging.env'))
    parser.add_argument('--out', help='where to write the rendered files (default: a new temporary folder)')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        raise SystemExit('--commit takes a full 40-character commit SHA: staging runs committed code only.')
    values = read_env(args.env)
    parts = [values.get(key, '') for key in ('REGION', 'PROJECT_ID', 'REPOSITORY', 'IMAGE_NAME')]
    image = '{}-docker.pkg.dev/{}/{}/{}:{}'.format(*parts, args.commit) if all(parts) else ''
    values.update(GIT_SHA=args.commit, IMAGE=image)  # a blank part leaves IMAGE blank, which render() refuses
    out = Path(args.out or tempfile.mkdtemp(prefix='vantage-render-'))
    out.mkdir(parents=True, exist_ok=True)
    for name, text in render(values).items():
        (out / name).write_text(text, encoding='utf-8')
        print(out / name)
    return 0


if __name__ == '__main__':
    sys.exit(main())
