import { formatMoney } from '../../../lib/format';
import cx from '../../../ui/cx';
import { TOTAL } from './boardConfig';

/*
 * Claude's chips (plan.md §8.14; F24, F25; the old `bnf-rule-chips`): each rule Work with Claude set on the board
 * ("Deductible (Single) < $2,000", "Diagnostic Tests doesn't contain “not covered”"), a chip that removes itself; the
 * person can only remove them. A rule on a column this line lacks rests, greyed, and applies on its own line. The
 * line's own "Monthly total ≤ $" is the input on the card, not a chip. Then Claude's pick (F25): "✦ Claude: label (n)
 * · k not judged", the plans it judged a match on one line; on another line it rests, greyed; a click removes it.
 */

const MONEY = ['amount', 'rate', 'rate4'];

function ruleWords(rule, fields, ops) {
  const field = fields[rule.key];
  const label = rule.key === TOTAL ? 'Monthly total' : (field?.label ?? rule.key);
  const op = ops.find((o) => o.key === rule.op)?.words ?? rule.op;
  let value = String(rule.value);
  if (rule.op === 'contains' || rule.op === 'excludes') value = `“${rule.value}”`;
  else if (rule.key === TOTAL || MONEY.includes(field?.type)) value = formatMoney(rule.value);
  else if (field?.type === 'percent') value = `${rule.value}%`;
  return `${label} ${op} ${value}`;
}

function pickTitle(pick, fields, lineLabel) {
  if (!pick.on) return `Judged on ${lineLabel(pick.line)} — it applies on that line. Click to remove.`;
  const on = pick.keys?.length ? ` on ${pick.keys.map((key) => fields[key]?.label ?? key).join(', ')}` : '';
  return `The plans Claude judged a match${on}. Plans it did not read are hidden too. Click to remove.`;
}

export default function RuleChips({ rules, fields, ops, lineLabel, pick = null, pickLineLabel, onRemove, onClearPick }) {
  const chips = [
    ...rules.applied.filter((rule) => rule !== rules.totalCap).map((rule) => ({ rule, on: true })),
    ...rules.resting.map((rule) => ({ rule, on: false })),
  ];
  if (!chips.length && !pick) return null;
  return (
    <div className="bnf-advisor-labelrow">
      <span className="bnf-advisor-views-label">Claude</span>
      <div className="bnf-rule-chips">
        {chips.map(({ rule, on }) => (
          <button
            key={[rule.key, rule.op, rule.value, rule.line ?? ''].join('~')}
            type="button"
            className={cx('bnf-rule-chip', !on && 'is-off')}
            title={on ? 'Remove this rule' : `${lineLabel} has no such column — the rule rests here and applies on its own line`}
            onClick={() => onRemove(rule)}
          >
            {ruleWords(rule, fields, ops)} ✕
          </button>
        ))}
        {pick && (
          <button
            type="button"
            className={cx('bnf-pick-chip', !pick.on && 'is-off')}
            title={pickTitle(pick, fields, pickLineLabel ?? ((key) => key))}
            onClick={onClearPick}
          >
            ✦ Claude: {pick.label} ({pick.plan_ids.length})
            {pick.on && pick.unjudged > 0 ? ` · ${pick.unjudged} not judged` : ''} ✕
          </button>
        )}
      </div>
    </div>
  );
}
