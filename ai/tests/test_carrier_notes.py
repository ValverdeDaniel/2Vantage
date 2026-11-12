"""Admins' carrier notes (plan.md §10.6; D119, OQ4): the note of a file's carrier rides each read's per-call note, and a
turn carries the notes of the deal's carriers, both outside the cached prefix."""

from ai import carrier_notes, services
from ai.models import CarrierNote
from ai.testing import text_block, turn_key
from documents.tests.helpers import stored

NOTE = 'Prints its HSA plans as two plan numbers.'


def test_D119_a_reads_note_carries_its_carriers_note(db):
    CarrierNote.objects.create(carrier='florida_blue', text=NOTE)
    assert carrier_notes.note_for_read('Filed as a renewal.', 'BCBS of Florida').endswith(f'- Florida Blue: {NOTE}')
    assert carrier_notes.note_for_read('Filed as a renewal.', 'Aetna') == 'Filed as a renewal.'
    assert carrier_notes.note_for_read('Filed as a renewal.', '') == 'Filed as a renewal.'


def test_D119_a_turn_carries_the_deals_carrier_notes_outside_the_cache(user, deal, fake_claude):
    CarrierNote.objects.create(carrier='aetna', text=NOTE)
    stored(user, deal, name='aetna.pdf', kind='quote', carrier='Aetna')
    fake_claude.record(turn_key('Hello', 1), content=[text_block('Hi.')])
    services.send_message(user, deal, text='Hello')
    params = fake_claude.log[0]['params']
    assert NOTE not in params['system'][0]['text']
    assert '<carrier-notes>' in params['messages'][-1]['content'][-2]['text']
    assert NOTE in params['messages'][-1]['content'][-2]['text']
