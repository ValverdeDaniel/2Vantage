import { useId, useState } from 'react';
import { formatMoney, formatPercent } from '../../lib/format';
import cx from '../../ui/cx';
import { changeText, enrollmentKeys, enrollmentText, SOURCE_WORDS } from './display';
import PlanHeaderCell from './PlanHeaderCell';
import ValueCell from './ValueCell';

function CostRow({ label, plans, render }) {
  return (
    <tr className="bnf-computed-row">
      <th scope="row" className="bnf-benefit-col">
        {label}
      </th>
      {plans.map((plan) => (
        <td key={plan.id} className={cx('bnf-cell bnf-computed', plan.role === 'current' && 'bnf-plan-col-current')}>
          {render(plan)}
        </td>
      ))}
    </tr>
  );
}

function noPrice(plan) {
  return <span className="bnf-delta-base">No price: {plan.premium?.reason_words ?? 'not priced'}</span>;
}

// A group's band row (the old `bnf-group-row`), whose label folds the group away and back.
function GroupRow({ label, span, collapsed, onToggle }) {
  return (
    <tr className="bnf-group-row">
      <td colSpan={span}>
        {onToggle ? (
          <button type="button" className="bnf-card-toggle" aria-expanded={!collapsed} onClick={onToggle}>
            <span className={cx('bnf-req-chevron', !collapsed && 'expanded')} aria-hidden="true">
              ▶
            </span>{' '}
            <span className="bnf-group-label">{label}</span>
          </button>
        ) : (
          <span className="bnf-group-label">{label}</span>
        )}
      </td>
    </tr>
  );
}

/**
 * The plan × field table (plan.md §8.14; 2V's simplified Advisor, F134), in the old Proposal grid's look
 * (`bnf-compare-table`, plans as columns). Rows are the line's field groups, then the Cost Summary.
 */
export default function PlanTable({ comparison, fieldsByKey, hideEmpty, actions }) {
  const [collapsed, setCollapsed] = useState({});
  const idBase = useId();
  const plans = comparison.plans;
  const byId = Object.fromEntries(plans.map((plan) => [plan.id, plan]));
  const keys = enrollmentKeys(comparison.rate_basis);
  const hasRenewal = plans.some((plan) => plan.role === 'renewal');
  const sameRole = (plan) => plans.filter((p) => p.role === plan.role);
  const span = plans.length + 1;

  return (
    <div className="bb-grid-card">
      <div className="bb-grid-scroll gk-grid">
        <table className="bnf-compare-table">
          <thead>
            <tr>
              <th scope="col" className="bnf-benefit-col">
                Benefit
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
                <GroupRow
                  label={group.label}
                  span={span}
                  collapsed={isCollapsed}
                  onToggle={() => setCollapsed((prev) => ({ ...prev, [group.key]: !prev[group.key] }))}
                />
                {!isCollapsed &&
                  rows.map((key) => {
                    const field = fieldsByKey[key];
                    const labelId = `${idBase}-${key}`;
                    return (
                      <tr key={key}>
                        <th scope="row" id={labelId} className="bnf-benefit-col">
                          {field.label}
                          {field.required && <span title="Required"> *</span>}
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
          <tbody>
            <GroupRow label="Cost Summary" span={span} />
            <CostRow
              label="Enrollment used"
              plans={plans}
              render={(plan) =>
                plan.enrollment_used ? (
                  <>
                    {enrollmentText(plan.enrollment_used, keys)}{' '}
                    <span className="bnf-delta-base">
                      ({SOURCE_WORDS[plan.enrollment_source] ?? plan.enrollment_source})
                    </span>
                  </>
                ) : (
                  <span className="bnf-delta-base">None yet</span>
                )
              }
            />
            <CostRow
              label="Monthly premium"
              plans={plans}
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
                  <span className="bnf-delta">{changeText(plan.change)}</span>
                ) : plan.part_of ? (
                  <span className="bnf-delta-base">Part of {plan.part_of}&apos;s enrollment — see packages</span>
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
    </div>
  );
}
