import { useRef, useState } from 'react';
import { formatDate } from '../../../lib/format';

/**
 * One note (M74–M77; old 891f1b3 `CaseNotes.jsx` noteRow): its kind badge, date and author; Pin / Unpin, Edit and
 * Delete for its author or an admin (`can_edit`), on hover and on focus (X-14). Edit is the old in-place textarea:
 * blur saves, Escape cancels, an unchanged body sends nothing. The card does the writing.
 */
export default function NoteItem({ note, busy, onPin, onSave, onDelete }) {
  const [draft, setDraft] = useState(null); // the body while editing
  const cancelled = useRef(false); // Escape: the blur that follows saves nothing
  const save = () => {
    const text = (draft || '').trim();
    setDraft(null);
    if (cancelled.current) {
      cancelled.current = false;
      return;
    }
    if (text && text !== note.body) onSave(note, text);
  };
  return (
    <div className={`bnf-ov-note ${note.pinned ? 'is-pinned' : ''}`}>
      <div className="bnf-ov-note-head">
        <span className={`bb-badge bnf-ov-note-kind bnf-ov-kind-${note.kind}`}>{note.kind_label}</span>
        <span className="bb-drop-meta">{formatDate(note.created_at)}</span>
        {note.author && <span className="bb-drop-meta">· {note.author.name}</span>}
        {note.can_edit && (
          <span className="bnf-ov-note-actions">
            <button
              type="button"
              className="bnf-override-link"
              disabled={busy}
              title={note.pinned ? 'Unpin' : 'Pin to the top'}
              onClick={() => onPin(note)}
            >
              {note.pinned ? 'Unpin' : 'Pin'}
            </button>
            <button
              type="button"
              className="bnf-override-link"
              disabled={busy}
              onClick={() => {
                cancelled.current = false;
                setDraft(note.body);
              }}
            >
              Edit
            </button>
            <button type="button" className="bnf-override-link bb-rose" disabled={busy} onClick={() => onDelete(note)}>
              Delete
            </button>
          </span>
        )}
      </div>
      {draft !== null ? (
        <textarea
          className="bnf-ov-note-input"
          autoFocus
          rows={3}
          value={draft}
          aria-label="Edit the note"
          onChange={(event) => setDraft(event.target.value)}
          onBlur={save}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              cancelled.current = true;
              setDraft(null);
            }
          }}
        />
      ) : (
        <div className="bnf-ov-note-body">{note.body}</div>
      )}
    </div>
  );
}
