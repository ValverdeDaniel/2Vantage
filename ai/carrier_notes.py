"""Admins' carrier notes in Claude's calls (plan.md §10.6; D119, OQ4; slice 24).

An admin keeps one note per carrier in Django admin ("Florida Blue prints its HSA plans as two plan numbers"). Every
call about that carrier carries the note in its per-call note, outside the cached prefix, so a changed note never
spoils the cache: a read adds the note of the carrier its file was filed under, a turn the notes of the carriers on
the deal's plans and files. Notes are the firm's words about how carriers print their files, never a client's data.
"""

from deals import carriers

from .models import CarrierNote

MAX_NOTES = 6  # a turn names at most this many carriers' notes (the old MAX_LESSON_CARRIERS was 4)


def _keys(names):
    out = []
    for name in names:
        key = carriers.match(name or '')
        if key and key not in out:
            out.append(key)
    return out


def text_for(names):
    """The notes of the carriers `names` mean, as one block of text ('' when there are none)."""
    keys = _keys(names)
    if not keys:
        return ''
    notes = {note.carrier: note.text for note in CarrierNote.objects.filter(carrier__in=keys)}
    lines = [
        f'- {carriers.BY_KEY[key]["name"]}: {" ".join(notes[key].split())}' for key in keys[:MAX_NOTES] if key in notes
    ]
    if not lines:
        return ''
    return (
        "The firm's notes on these carriers' files (follow them unless a file plainly says otherwise):\n"
        + '\n'.join(lines)
    )


def note_for_read(note, carrier):
    """A read's per-call note with its file's carrier note after it."""
    extra = text_for([carrier])
    return f'{note}\n\n{extra}' if extra else note
