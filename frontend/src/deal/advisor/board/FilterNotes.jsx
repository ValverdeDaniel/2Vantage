/*
 * The filter card's amber notes (plan.md §8.14; F10, F18, F140): what the filters cannot judge, said rather than
 * hidden. Plans with no price yet under the budget or a total cap are named ("2 have no price yet — enter
 * enrollment"), with the summary tiers card one click away on a tier-rated line; priced plans with no Δ vs current
 * (nothing replaced, or only part of a plan's people) are named under the budget too; and a line with no current plan
 * says the budget and closest-to-current are off.
 */

const SHOWN = 3;

function names(plans) {
  const named = plans.slice(0, SHOWN).map((plan) => `${plan.carrier} ${plan.name}`.trim());
  const more = plans.length - named.length;
  return more > 0 ? `${named.join(', ')} and ${more} more` : named.join(', ');
}

function has(count) {
  return `${count} ${count === 1 ? 'has' : 'have'}`;
}

/** The words for plans with no price: their own reason when they share one, else "enter enrollment". */
function reasonOf(plans) {
  const reasons = new Set(plans.map((plan) => plan.premium?.reason_words || 'enter enrollment'));
  return reasons.size === 1 ? [...reasons][0] : 'enter enrollment';
}

export default function FilterNotes({ unpriced, uncompared, noCurrent, onCounts }) {
  const reason = unpriced.length ? reasonOf(unpriced) : '';
  return (
    <>
      {noCurrent && (
        <span className="bnf-filter-note">No current plan on this line — the budget band and closest-to-current are inactive.</span>
      )}
      {unpriced.length > 0 && (
        <span className="bnf-filter-note" role="status">
          {has(unpriced.length)} no price yet —{' '}
          {onCounts && reason === 'enter enrollment' ? (
            <button type="button" className="bnf-pv-doclink" onClick={onCounts}>
              enter enrollment
            </button>
          ) : (
            reason
          )}
          : {names(unpriced)}
        </span>
      )}
      {uncompared.length > 0 && (
        <span className="bnf-filter-note" role="status">
          {has(uncompared.length)} no Δ vs current, so the budget cannot judge {uncompared.length === 1 ? 'it' : 'them'}:{' '}
          {names(uncompared)}
        </span>
      )}
    </>
  );
}
