import { useState } from 'react';
import { useTrayAsk } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

/*
 * The census By person (plan.md §8.8; C30, L46; old 891f1b3 `CensusRequestPanel.jsx` "By person"): each person with
 * their blank cells, the required ones first; pick cells (or a person's whole row) and "＋ Ask N" puts them in the
 * request tray — the same asks as By field, one value each. The server lists at most 500 cells and says how many more.
 */
export default function CensusLens({ dealId, lens, readOnly }) {
  const [picked, setPicked] = useState(new Set());
  const ask = useTrayAsk(dealId);
  const toast = useToast();
  const flip = (refs) =>
    setPicked((now) => {
      const next = new Set(now);
      const all = refs.every((ref) => next.has(ref));
      refs.forEach((ref) => (all ? next.delete(ref) : next.add(ref)));
      return next;
    });
  const askPicked = () =>
    ask
      .mutateAsync({ refs: [...picked], skip_out: true })
      .then((answer) => {
        toast.success(`${answer.added} added to the request tray`);
        setPicked(new Set());
      })
      .catch((error) => toast.error(errorText(error)));
  if (!lens.people.length) return <div className="bnf-review-empty">Nobody on the roster has a blank to ask about.</div>;
  return (
    <div className="bb-grid-card">
      <div className="bnf-review-boardhead">
        <div className="bnf-review-count">
          {lens.total} blank{lens.total === 1 ? '' : 's'}
          {lens.truncated && ` · showing the first ${lens.shown}`}
          {picked.size > 0 && <> · <b>{picked.size}</b> selected</>}
        </div>
        {picked.size > 0 && !readOnly && (
          <button type="button" className="btn btn-violet btn-sm" disabled={ask.isPending} onClick={askPicked}>
            ＋ Ask {picked.size}
          </button>
        )}
      </div>
      <div className="bnf-review-people">
        {lens.people.map((person) => {
          const refs = person.cells.map((cell) => cell.ref);
          return (
            <div key={person.id} className={`bnf-review-person${person.kind === 'dependent' ? ' bnf-review-person-dep' : ''}`}>
              <label className="bnf-review-check">
                <input type="checkbox" disabled={readOnly} checked={refs.every((ref) => picked.has(ref))} onChange={() => flip(refs)} />
                <b>{person.title}</b> · {person.cells.length} blank{person.cells.length === 1 ? '' : 's'}
              </label>
              <div className="bnf-review-layers">
                {person.cells.map((cell) => (
                  <label key={cell.ref} className="bnf-review-check">
                    <input type="checkbox" disabled={readOnly} checked={picked.has(cell.ref)} onChange={() => flip([cell.ref])} />
                    {cell.label}
                    {cell.required && <span className="bnf-qb-star" title="Required on this deal">*</span>}
                  </label>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
