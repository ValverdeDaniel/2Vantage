"""Names and stray bytes (plan.md §6.3; E95, E98)."""

import io
import os
from datetime import date

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command

from documents.selectors import display_name

from .helpers import stored


def test_E95_unnamed_renewal_invoice_and_claims_files_read_as_their_plan_year(user, deal):
    deal.effective_date = date(2027, 1, 1)
    deal.save(update_fields=['effective_date'])
    renewal = stored(user, deal, name='scan0042.pdf', kind='renewal')
    assert display_name(renewal) == '2027 Renewal / rates'
    named = stored(user, deal, name='scan0043.pdf', kind='invoice', label='October list bill')
    assert display_name(named) == 'October list bill'
    assert display_name(stored(user, deal, name='quote.pdf', kind='quote')) == 'quote.pdf'


def test_E98_sweep_lists_stray_bytes_without_names_and_deletes_only_when_asked(user, deal, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)  # a storage of this test's own
    kept = stored(user, deal)
    stray = default_storage.save(f'deals/{deal.id}/stray-Tester Alpha census.pdf', ContentFile(b'%PDF-1.4'))
    out = io.StringIO()
    call_command('sweep_orphan_files', stdout=out)
    assert out.getvalue().startswith('1 stray file') and 'Tester' not in out.getvalue()
    assert default_storage.exists(stray)
    call_command('sweep_orphan_files', '--delete', stdout=io.StringIO())
    assert not default_storage.exists(stray) and os.path.exists(kept.file.path)
