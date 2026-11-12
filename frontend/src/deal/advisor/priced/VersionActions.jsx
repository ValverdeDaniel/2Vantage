import { pricedKind } from '../board/chips';

/*
 * A plan's priced-version buttons in ✎ Edit (plan.md §8.14; F76, F83; the old `editact` column): ＋ opens a live draft
 * right under the plan (the in-force plan takes only a premium holiday); on a priced version ✎ reopens its editor,
 * which re-prices it from the original, and ✕ removes it — the original stays, and Undo brings the version back.
 */
export default function VersionActions({ plan, ui }) {
  const kit = ui.priced;
  if (!kit) return null;
  const version = Boolean(pricedKind(plan));
  let addTitle =
    'Add a concession, a bundling discount or a premium holiday to this plan — the original is never overwritten';
  if (plan.role === 'current') {
    addTitle =
      'Add a premium holiday against the in-force baseline — the only priced version the current plan can take';
  }
  if (plan.sold) addTitle = 'Sold — final rates are confirmed with the carrier at close-out, not re-priced here';
  return (
    <span className="bnf-conc-actions">
      {version && (
        <button
          type="button"
          className="btn btn-secondary btn-sm bnf-pv-add"
          title="Edit this priced version — reopens the formula editor and re-prices from the original"
          aria-label={`Edit the priced version ${plan.name}`}
          onClick={() => kit.edit(plan)}
        >
          ✎
        </button>
      )}
      <button
        type="button"
        className="btn btn-secondary btn-sm bnf-pv-add"
        title={addTitle}
        aria-label={`Price a version of ${plan.carrier} ${plan.name}`}
        disabled={plan.sold}
        onClick={() => kit.open(plan)}
      >
        ＋
      </button>
      {version && (
        <button
          type="button"
          className="btn btn-secondary btn-sm bnf-conc-remove"
          title="Remove this priced version (the original stays)"
          aria-label={`Remove the priced version ${plan.name}`}
          onClick={() => ui.actions.remove([plan.id])}
        >
          ✕
        </button>
      )}
    </span>
  );
}
