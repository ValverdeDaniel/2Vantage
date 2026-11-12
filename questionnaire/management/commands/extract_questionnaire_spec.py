"""manage.py extract_questionnaire_spec — regenerate Florida Blue's carrier data module (G124). A dev command: the app
never runs it.

    python manage.py extract_questionnaire_spec --template assets/questionnaires/fl_blue_51_uw_v9.template.xml
    python manage.py extract_questionnaire_spec --pdf <the carrier's XFA original> [--write]

Prints the module (or, with --write, replaces `questionnaire/forms/fl_blue_51_data.py`), and with --check exits 1 when
the committed module differs from what the template gives.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from questionnaire.xfa.parse import extract_xfa_streams, parse_template
from questionnaire.xfa.render import render_data_module

TARGET = Path(__file__).resolve().parents[2] / 'forms' / 'fl_blue_51_data.py'


class Command(BaseCommand):
    help = "Regenerate questionnaire/forms/fl_blue_51_data.py from the carrier's XFA template (dev only)."

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument('--template', help='the template packet, as XML')
        source.add_argument('--pdf', help="the carrier's original XFA PDF")
        parser.add_argument('--write', action='store_true', help='replace the committed data module')
        parser.add_argument('--check', action='store_true', help='exit 1 when the committed module differs')

    def handle(self, *args, **options):
        try:
            if options['template']:
                xml = Path(options['template']).read_bytes()
            else:
                xml = extract_xfa_streams(Path(options['pdf']).read_bytes())['template']
            text = render_data_module(parse_template(xml))
        except (OSError, ValueError) as error:
            raise CommandError(str(error)) from error
        if options['check']:
            if TARGET.read_text(encoding='utf-8') != text:
                raise CommandError('fl_blue_51_data.py differs from what the template gives: regenerate it.')
            self.stdout.write('fl_blue_51_data.py matches the template.')
        elif options['write']:
            TARGET.write_text(text, encoding='utf-8', newline='\n')
            self.stdout.write(f'Wrote {TARGET.name}.')
        else:
            self.stdout.write(text, ending='')
