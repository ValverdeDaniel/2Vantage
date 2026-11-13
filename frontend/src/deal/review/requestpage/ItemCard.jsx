import NoteThread from '../thread/NoteThread';
import { chipWords, STATUS_CLASSES } from './requestModel';

// What "To client" does on an item no question of theirs is open on: an ask for a blank, a send-back for a value.
function askOf(item) {
  if (item.status === 'asked' || item.status === 'in_cart') return null;
  if (item.status === 'missing') {
    return { kind: 'ask', label: 'Add to tray', hint: 'Asks for it, with your note · waits in the request tray', placeholder: 'What should they fill in?' };
  }
  return { kind: 'sendback', label: 'Send back', hint: 'Sends it back to check, with your note · waits in the request tray', placeholder: 'What should they check?' };
}

/*
 * One item's card beside the ask list (plan.md §8.8; L22, L31 in part; old 891f1b3 `RequestCards.jsx`): what it is,
 * where it stands, what we hold, and its thread — the team's notes, what went to the client, their questions and our
 * replies — with a composer: a note to the team, a note to the client now (on a link that asks it), our reply to
 * their open question, or, on an item not out with them, an ask or send-back with a note into the request tray. The
 * margin of cards beside their form is slice 57's; this is the one card the list picked.
 */
export default function ItemCard({ item, thread, labels, kindWords, newSince, readOnly, propsFor, onClose }) {
  if (!item) return null;
  const words = chipWords(item, labels);
  return (
    <div className="rr-dest rr-dest-on" aria-label={`${item.label}: its thread`}>
      <div className="rr-dest-head">
        <div>
          <b>{item.label}</b>
          <span>
            {item.section}
            {item.value ? ` · ${item.value}` : ''}
          </span>
        </div>
        <button type="button" className="rr-snippet-close" aria-label="Close" title="Close its card" onClick={onClose}>
          ×
        </button>
      </div>
      {words && <span className={`rr-rail-chip ${STATUS_CLASSES[item.status] || ''}`}>{words}</span>}
      <NoteThread
        notes={thread}
        kindWords={kindWords}
        newSince={newSince}
        readOnly={readOnly}
        defaultAudience="client"
        {...propsFor({ ref: item.ref, ask: askOf(item) })}
      />
    </div>
  );
}
