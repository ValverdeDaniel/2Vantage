import { useState } from 'react';
import { useRevertActivity } from '../../../api/deals';
import { useMeta } from '../../../api/meta';
import { useAddNote, useDeleteNote, useEditNote, useNotes } from '../../../api/notes';
import { errorText } from '../../../lib/errors';
import InlineError from '../../../ui/InlineError';
import { useToast } from '../../../ui/useToast';
import NoteItem from './NoteItem';

/**
 * The deal's notepad (plan.md §8.6; M73–M77; old Vantage 891f1b3 `CaseNotes.jsx`): the composer — the text, the five
 * kinds as chips (the words are /api/meta/'s `note_kinds`) and Add note — then the notes, pinned first in amber,
 * newest first. Pin, edit and delete go through deals' note doors (author or admin); a delete is soft and its toast's
 * Undo reverts it (deals' `activity/{id}/revert/`). Shared: the deal's Overview mounts it, and the client page mounts
 * it on the current deal (slice 67) with its own words. Earlier deals' notes wait with renewals (M78).
 */
export default function NotesCard({
  dealId,
  title = 'Notes',
  sub = 'What happened, in your words. Internal — the client never sees these.',
}) {
  const [body, setBody] = useState('');
  const [kind, setKind] = useState('note');
  const meta = useMeta().data;
  const notes = useNotes(dealId);
  const add = useAddNote(dealId);
  const edit = useEditNote(dealId);
  const remove = useDeleteNote(dealId);
  const revert = useRevertActivity(dealId);
  const toast = useToast();
  const busy = add.isPending || edit.isPending || remove.isPending;
  const failed = (fallback) => (error) => toast.error(errorText(error, { fallback }));

  const submit = (event) => {
    event.preventDefault();
    const text = body.trim();
    if (!text || busy) return;
    add
      .mutateAsync({ body: text, kind })
      .then(() => {
        setBody('');
        setKind('note');
        toast.success('Note added');
      })
      .catch(failed('Could not save that note.'));
  };

  const undo = (activityId) =>
    revert.mutate(activityId, {
      onSuccess: () => toast.success('Note restored'),
      onError: failed('Could not bring that note back.'),
    });

  const onDelete = (note) =>
    remove
      .mutateAsync(note.id)
      .then((answer) =>
        toast.show(
          <span>
            Note deleted ·{' '}
            <button type="button" className="bnf-linklike" onClick={() => undo(answer.activity_id)}>
              Undo
            </button>
          </span>,
          { duration: 8000 },
        ),
      )
      .catch(failed('Could not delete that note.'));

  const onPin = (note) => edit.mutateAsync({ id: note.id, pinned: !note.pinned }).catch(failed('Could not pin that note.'));
  const onSave = (note, text) => edit.mutateAsync({ id: note.id, body: text }).catch(failed('Could not update that note.'));
  const rows = notes.data || [];

  return (
    <div className="bb-panel bnf-ov-notes">
      <div className="bb-panel-title">{title}</div>
      <div className="bb-panel-sub">{sub}</div>
      <form className="bnf-ov-note-form" onSubmit={submit}>
        <textarea
          className="bnf-ov-note-input"
          rows={3}
          aria-label="A new note"
          placeholder="Called Rebecca — she's chasing the census from payroll…"
          value={body}
          onChange={(event) => setBody(event.target.value)}
        />
        <div className="bnf-ov-note-formfoot">
          <div className="bnf-ov-kindchips" role="group" aria-label="Kind of note">
            {(meta?.note_kinds || []).map((entry) => (
              <button
                type="button"
                key={entry.key}
                aria-pressed={kind === entry.key}
                className={`bnf-chip ${kind === entry.key ? 'bnf-chip-on' : ''}`}
                onClick={() => setKind(entry.key)}
              >
                {entry.label}
              </button>
            ))}
          </div>
          <button className="btn btn-primary btn-sm" type="submit" disabled={busy || !body.trim()}>
            Add note
          </button>
        </div>
      </form>
      {notes.isError && (
        <InlineError compact title="Could not load the notes." error={notes.error} onRetry={() => notes.refetch()} />
      )}
      <div className="bnf-ov-notelist">
        {notes.isSuccess && rows.length === 0 && <div className="bb-subtitle">No notes on this deal yet.</div>}
        {rows.map((note) => (
          <NoteItem key={note.id} note={note} busy={busy} onPin={onPin} onSave={onSave} onDelete={onDelete} />
        ))}
      </div>
    </div>
  );
}
