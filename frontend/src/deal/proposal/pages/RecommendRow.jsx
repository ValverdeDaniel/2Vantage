import cx from '../../../ui/cx';

/*
 * "Our recommendation" under a page's rows in the builder (plan.md §5.4, §8.14; J52; the old ProposalPages.jsx
 * `recommendRow` at 891f1b3): Recommend / Recommended under each option, and Keep this plan / Keeping this plan under a
 * current plan something on the proposal could replace (OQ37: a current plan may be recommended, as the old app did).
 * Several plans a line may be recommended (§5.4); a click toggles the plan's own mark through quotes' door. Shut while
 * the line has a sold plan: the sale is the line's answer.
 */
export default function RecommendRow({ plans, keepable, disabled, busy, onChoose }) {
  return (
    <tr className="bnf-pg-rec">
      <th scope="row">Our recommendation</th>
      {plans.map((plan) => {
        const current = plan.kind === 'current';
        if (current && !keepable.includes(plan.plan_id)) {
          return <td key={plan.plan_id} className="is-current" />;
        }
        const picked = plan.recommended;
        return (
          <td key={plan.plan_id} className={current ? 'is-current' : ''}>
            <button
              type="button"
              className={cx('bnf-pg-recbtn', picked && 'is-picked')}
              aria-pressed={picked}
              disabled={busy || disabled}
              onClick={() => onChoose(plan)}
            >
              {picked ? '✓ ' : ''}
              {current ? (picked ? 'Keeping this plan' : 'Keep this plan') : picked ? 'Recommended' : 'Recommend'}
            </button>
          </td>
        );
      })}
    </tr>
  );
}
