/*
 * The client's budget, from the intake's Goals card, as hints on the filter card (plan.md §8.14; F139; OQ51 default:
 * a hint with Apply, never prefilled, since the target may cover every line). Pure.
 * - "Client target $X/mo · Apply" sets this line's "Monthly total ≤ $" to the target (F19's rule).
 * - "Client accepts up to N% · Apply" sets the budget select to its most generous step that stays inside N (the
 *   steps come from /api/meta/ `board.budget`): 8% applies "Within 5% of current"; below every step, no Apply.
 * The answers are stored cleaned (intake's one cleaner: "62000", "8"), so they are read, never worked out here.
 */
import { TOTAL } from './boardConfig';

function number(text) {
  if (text == null || text === '') return null;
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

/** {target, increase}: the Monthly Budget Target and the Acceptable Increase as numbers, or null when unanswered. */
export function clientBudget(answers) {
  return { target: number(answers?.budget_target), increase: number(answers?.acceptable_increase_pct) };
}

/** The stored amount with thousands commas and its own decimals ("62000" → "$62,000"): shown, never rounded. */
export function dollars(value) {
  const [whole, decimals] = String(value).split('.');
  const sign = whole.startsWith('-') ? '−' : '';
  const digits = whole.replace('-', '').replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${sign}$${digits}${decimals ? `.${decimals}` : ''}`;
}

/** The budget step Apply picks for an acceptable increase of `pct`: the largest step at or under it, else null. */
export function budgetStep(steps, pct) {
  if (pct == null) return null;
  const inside = (steps ?? []).filter((step) => step.value !== null && step.value <= pct);
  if (!inside.length) return null;
  return inside.reduce((best, step) => (step.value > best.value ? step : best));
}

/** This line's "Monthly total ≤ $" amount, or null. */
export function totalCapOf(config, line) {
  const rule = (config.rules ?? []).find((r) => r.key === TOTAL && r.op === '<=' && r.line === line);
  return rule ? rule.value : null;
}
