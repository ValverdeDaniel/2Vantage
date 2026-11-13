import ItemCard from '../requestpage/ItemCard';
import { chipWords, STATUS_CLASSES } from '../requestpage/requestModel';

const EXCERPT = 90;

/*
 * One card in the comment margin (plan.md §8.8; L31; old 891f1b3 `RequestCards.jsx` `rr-rcard`): folded, the item's
 * label, where it stands and the newest word of its thread; a client's question offers "Enter it" (edit mode, L34)
 * and "Reply ▸"; an answer back offers "Review ▸" (the queue). Picked, it opens whole: the item card with its thread and
 * composer (L22). The comment margin places it beside the item in their form.
 */
export default function MarginCard({ item, thread, picked, labels, kindWords, newSince, readOnly, propsFor, onPick, onClose, onEdit, onReview }) {
  if (picked) {
    return (
      <ItemCard item={item} thread={thread} labels={labels} kindWords={kindWords} newSince={newSince} readOnly={readOnly}
        propsFor={propsFor} onClose={onClose} />
    );
  }
  const last = thread[thread.length - 1];
  const text = last?.text || '';
  const fresh = newSince ? thread.some((note) => note.from_client && note.at > newSince) : false;
  const words = chipWords(item, labels);
  return (
    <div className={`rr-rcard${fresh ? ' rr-rcard-new' : ''}`} role="button" tabIndex={0} onClick={() => onPick(item.ref)}
      onKeyDown={(event) => event.key === 'Enter' && onPick(item.ref)}>
      <div className="rr-rcard-head">
        <span className="rr-rcard-label">{item.label}</span>
        {thread.length > 0 && <span className="rr-rcard-count">💬 {thread.length}</span>}
      </div>
      {words && <span className={`rr-rail-chip ${STATUS_CLASSES[item.status] || ''}`}>{words}</span>}
      {text && (
        <div className="rr-rcard-last">
          {last.from_client ? `${last.who || 'The client'}: ` : ''}
          {text.length > EXCERPT ? `${text.slice(0, EXCERPT - 1)}…` : text}
        </div>
      )}
      {!readOnly && (
        <div className="rr-rcard-quick" onClick={(event) => event.stopPropagation()} role="presentation">
          {item.status === 'question' && (
            <>
              <button type="button" className="rr-rcard-quickbtn" onClick={() => onEdit(item)} title="Type their answer in yourself, in edit mode">
                Enter it
              </button>
              <button type="button" className="rr-rcard-quickbtn" onClick={() => onPick(item.ref)}>
                Reply ▸
              </button>
            </>
          )}
          {item.status === 'answered' && (
            <button type="button" className="rr-rcard-quickbtn" onClick={() => onReview(item)} title="Approve it, keep ours, or send it back, in the review queue">
              Review ▸
            </button>
          )}
        </div>
      )}
    </div>
  );
}
