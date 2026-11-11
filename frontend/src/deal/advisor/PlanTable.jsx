import { useId, useState } from 'react';
import { formatMoney, formatPercent } from '../../lib/format';
import cx from '../../ui/cx';
import { changeText, enrollmentKeys, enrollmentText, SOURCE_WORDS } from './display';
import PlanHeaderCell from './PlanHeaderCell';
import styles from './PlanTable.module.css';
import ValueCell from './ValueCell';

function CostRow({ label, plans, render, strong }) {
  return (
    <tr className={cx(styles.costRow, strong && styles.strong)}>
      <th scope="row" className={styles.rowLabel}>
        {label}
      </th>
      {plans.map((plan) => (
        <td key={plan.id} className={styles.costCell}>
          {render(plan)}
        </td>
      ))}
    </tr>
  );
}

function noPrice(plan) {
  return <span className={styles.reason}>No price: {plan.premium?.reason_words ?? 'not priced'}</span>;
}

/** The plan × field table (plan.md §8.11). Columns are plans; rows are the line's field groups, then the cost rows. */
export default function PlanTable({ comparison, fieldsByKey, hideEmpty, actions }) {
  const [collapsed, setCollapsed] = useState({});
  const idBase = useId();
  const plans = comparison.plans;
  const byId = Object.fromEntries(plans.map((plan) => [plan.id, plan]));
  const keys = enrollmentKeys(comparison.rate_basis);
  const hasRenewal = plans.some((plan) => plan.role === 'renewal');
  const sameRole = (plan) => plans.filter((p) => p.role === plan.role);

  return (
    <div className={styles.scroller}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col" className={styles.corner}>
              <span className={styles.srOnly}>Field</span>
            </th>
            {plans.map((plan) => {
              const peers = sameRole(plan);
              return (
                <PlanHeaderCell
                  key={plan.id}
                  plan={plan}
                  byId={byId}
                  actions={actions}
                  isFirst={peers[0]?.id === plan.id}
                  isLast={peers[peers.length - 1]?.id === plan.id}
                />
              );
            })}
          </tr>
        </thead>
        {comparison.groups.map((group) => {
          const rows = group.fields.filter(
            (key) => !hideEmpty || plans.some((plan) => (plan.values?.[key] ?? '') !== ''),
          );
          if (!rows.length) return null;
          const isCollapsed = collapsed[group.key];
          return (
            <tbody key={group.key}>
              <tr className={styles.groupRow}>
                <th scope="rowgroup" colSpan={plans.length + 1}>
                  <button
                    type="button"
                    className={styles.groupToggle}
                    aria-expanded={!isCollapsed}
                    onClick={() => setCollapsed((prev) => ({ ...prev, [group.key]: !prev[group.key] }))}
                  >
                    <span aria-hidden="true">{isCollapsed ? '▸' : '▾'}</span> {group.label}
                  </button>
                </th>
              </tr>
              {!isCollapsed &&
                rows.map((key) => {
                  const field = fieldsByKey[key];
                  const labelId = `${idBase}-${key}`;
                  return (
                    <tr key={key}>
                      <th scope="row" id={labelId} className={styles.rowLabel}>
                        {field.label}
                        {field.required && (
                          <span className={styles.required} title="Required">
                            {' '}
                            *
                          </span>
                        )}
                      </th>
                      {plans.map((plan) => (
                        <ValueCell key={plan.id} plan={plan} field={field} update={actions.update} labelId={labelId} />
                      ))}
                    </tr>
                  );
                })}
            </tbody>
          );
        })}
        <tbody className={styles.costBody}>
          <CostRow
            label="Enrollment used"
            plans={plans}
            render={(plan) =>
              plan.enrollment_used ? (
                <>
                  {enrollmentText(plan.enrollment_used, keys)}{' '}
                  <span className={styles.muted}>({SOURCE_WORDS[plan.enrollment_source] ?? plan.enrollment_source})</span>
                </>
              ) : (
                <span className={styles.reason}>None yet</span>
              )
            }
          />
          <CostRow
            label="Monthly premium"
            plans={plans}
            strong
            render={(plan) =>
              plan.premium?.monthly == null
                ? noPrice(plan)
                : `${formatMoney(plan.premium.monthly)}${plan.premium.quoted ? ' †' : ''}`
            }
          />
          <CostRow label="Annual premium" plans={plans} render={(plan) => formatMoney(plan.premium?.annual)} />
          <CostRow
            label="Change vs current"
            plans={plans}
            render={(plan) =>
              plan.change ? (
                changeText(plan.change)
              ) : plan.part_of ? (
                <span className={styles.muted}>Part of {plan.part_of}&apos;s enrollment — see packages</span>
              ) : (
                ''
              )
            }
          />
          {hasRenewal &&
            comparison.rate_basis === 'composite' &&
            ['EE', 'ES', 'EC', 'FAM'].map((tier) => (
              <CostRow
                key={tier}
                label={`Rate change — ${tier}`}
                plans={plans}
                render={(plan) => {
                  const change = plan.tier_rate_change?.[tier];
                  return change ? formatPercent(change.pct) : '';
                }}
              />
            ))}
        </tbody>
      </table>
    </div>
  );
}
