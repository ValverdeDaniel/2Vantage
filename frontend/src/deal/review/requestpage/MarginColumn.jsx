import CommentMargin from '../margin/CommentMargin';
import MarginCard from '../margin/MarginCard';
import { marginRefs } from '../margin/placeCards';

/*
 * The comment margin beside their form on a person's link (plan.md §8.8; L31; old 891f1b3 `RequestPage.jsx` the cards
 * column, D-162): a card per item with a conversation, an answer back or a question open, and the one picked, each
 * standing level with its item in their form (`data-ask-ref`; an item not on their form follows the card before).
 */
export default function MarginColumn({ items, threads, picked, frameRef, cardProps, onPick, onEdit, onReview }) {
  const refs = marginRefs(items, threads, picked);
  const byRef = Object.fromEntries((items || []).map((item) => [item.ref, item]));
  const anchorOf = (ref) => frameRef.current?.querySelector(`[data-ask-ref="${CSS.escape(ref)}"]`) || null;
  if (!refs.length) return <div className="rr-cards-none rr-edit-note">No conversation on this tab yet: pick an item to start one.</div>;
  return (
    <CommentMargin rootRef={frameRef} refs={refs} anchorOf={anchorOf} activeRef={picked || ''}>
      {(ref) => (
        <MarginCard {...cardProps} item={byRef[ref]} thread={threads[ref] || []} picked={ref === picked} onPick={onPick}
          onClose={() => onPick(null)} onEdit={onEdit} onReview={onReview} />
      )}
    </CommentMargin>
  );
}
