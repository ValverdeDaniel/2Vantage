import { useState } from 'react';

const ASKS = ['sendback', 'ask'];
const ASK_DEFAULT = 'Please check this and update it.';

function when(at) {
  if (!at) return '';
  const date = new Date(at);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Open, and ours to close: a client question nobody answered, or a send-back or ask that went out and is not answered.
function closable(note) {
  if (note.resolved_at) return false;
  return note.kind === 'question' || (ASKS.includes(note.kind) && Boolean(note.sent_at));
}

/*
 * One item's notes (plan.md §8.8; L22; old 891f1b3 `reviewrequest/NoteThread.jsx`): what the team said to itself (🔒,
 * never shown to the client), what went to the client, the client's own question and our reply. Props only; every
 * write is the host's.
 *
 * notes: [{id, kind, audience, text, by, who, at, sent_at, resolved_at, from_client}]; `kindWords` {kind: words} from
 * /api/meta/ `review.note_kinds`.
 * - `onSend(text, audience, {replyTo, ask})` -> Promise<boolean>: a composer, "To client" or "🔒 Team only". To the
 *   client with a question of theirs open, it is our reply to it, which closes it. With `clientAsk` and no question
 *   open, "To client" puts the item in the request tray carrying the note (it reaches them only once sent).
 * - `onResolve(id)`: Resolve on an open question, or on a send-back or ask that went out.
 * - `newSince`: a dot on each note newer than the reader's last look. `readOnly`: the notes alone.
 */
export default function NoteThread({
  notes,
  kindWords = {},
  clientName = 'The client',
  onSend = null,
  onResolve = null,
  newSince = null,
  defaultAudience = 'team',
  clientAsk = null,
  readOnly = false,
}) {
  const [text, setText] = useState('');
  const [audience, setAudience] = useState(defaultAudience);
  const [sending, setSending] = useState(false);
  const [resolving, setResolving] = useState(null);
  const list = notes || [];
  if (!list.length && (!onSend || readOnly)) return null;
  const since = newSince ? Date.parse(newSince) : NaN;
  const whoOf = (note) => note.who || (note.from_client ? clientName : note.by || 'Us');
  const openQuestion = [...list].reverse().find((note) => note.from_client && !note.resolved_at) || null;
  const toClient = audience === 'client';
  const asking = toClient && !openQuestion && Boolean(clientAsk);

  async function send() {
    const body = text.trim();
    if (!body || sending || !onSend) return;
    setSending(true);
    let ok = false;
    try {
      ok = await onSend(body, toClient ? 'client' : 'team', { replyTo: toClient && openQuestion ? openQuestion.id : null, ask: asking });
    } finally {
      setSending(false);
    }
    if (ok !== false) setText('');
  }

  async function resolve(id) {
    setResolving(id);
    try {
      await onResolve(id);
    } finally {
      setResolving(null);
    }
  }

  let hint = 'Team only';
  let placeholder = 'Only your team sees this…';
  let sendWords = 'Send';
  if (asking) {
    hint = clientAsk.hint || 'Goes in the request tray · sent with Send';
    placeholder = clientAsk.placeholder || 'What should they check or fill in?';
    sendWords = clientAsk.label || 'Add to tray';
  } else if (toClient) {
    hint = openQuestion ? 'Shows on their link now · answers their question' : 'Shows on their link now';
    placeholder = openQuestion ? `Your reply to ${whoOf(openQuestion)}…` : 'They see this on their secure link…';
    if (openQuestion) sendWords = 'Reply';
  }

  return (
    <div className="rr-thread">
      {list.map((note) => {
        const team = note.audience === 'team';
        const draft = ASKS.includes(note.kind) && !note.sent_at;
        const at = note.sent_at || note.at;
        const fresh = !Number.isNaN(since) && at && Date.parse(at) > since;
        return (
          <div key={note.id} className={`rr-thread-note${note.from_client ? ' rr-thread-client' : ''}${team ? ' rr-thread-team' : ''}`}>
            <div className="rr-thread-who">
              {fresh && <i className="rr-thread-dot" title="New since your last look" />}
              {team ? '🔒 ' : ''}
              {whoOf(note)}
              <span>
                {' · '}
                {kindWords[note.kind] || note.kind}
                {draft ? ' · in the tray, not sent yet' : ''}
                {team ? ' · team only' : ''}
                {note.resolved_at && note.kind === 'question' ? ' · answered' : ''}
                {note.resolved_at && ASKS.includes(note.kind) ? ' · closed' : ''}
                {when(at) ? ` · ${when(at)}` : ''}
              </span>
              {onResolve && !readOnly && closable(note) && (
                <button
                  type="button"
                  className="rr-thread-resolve"
                  disabled={resolving === note.id}
                  title={
                    note.kind === 'question'
                      ? 'Close their question without a reply (answered another way)'
                      : 'Close it: answered another way, or no longer needed'
                  }
                  onClick={() => resolve(note.id)}
                >
                  {resolving === note.id ? 'Resolving…' : 'Resolve'}
                </button>
              )}
            </div>
            <div className="rr-thread-text">{note.text || (ASKS.includes(note.kind) ? ASK_DEFAULT : '')}</div>
          </div>
        );
      })}
      {onSend && !readOnly && (
        <div className="rr-thread-compose">
          <div className="rr-audience" role="radiogroup" aria-label="Who sees it">
            <button
              type="button"
              className={`rr-audience-opt${toClient ? ' rr-audience-on' : ''}`}
              title={clientAsk && !openQuestion ? 'Write to the client: the note rides its ask in the tray, sent with Send' : 'Write to the client: it shows on their secure link'}
              onClick={() => setAudience('client')}
            >
              To client
            </button>
            <button
              type="button"
              className={`rr-audience-opt${!toClient ? ' rr-audience-on' : ''}`}
              title="A note only your team sees: never on the client's link"
              onClick={() => setAudience('team')}
            >
              🔒 Team only
            </button>
          </div>
          <textarea
            value={text}
            placeholder={placeholder}
            aria-label="Note"
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                send();
              } else if (event.key === 'Escape') event.target.blur();
            }}
          />
          <div className="rr-thread-compose-foot">
            <span className="rr-qi-hint">
              <b>{hint}</b>
              {` · Enter to ${asking ? 'add' : 'send'} · Shift+Enter for a new line`}
            </span>
            <button type="button" className={`btn btn-sm ${toClient ? 'btn-violet' : 'btn-secondary'}`} disabled={sending || !text.trim()} onClick={send}>
              {sending ? 'Sending…' : sendWords}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
