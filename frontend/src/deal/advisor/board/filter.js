/*
 * The board's filters (plan.md §8.14; F18–F24, F26, F27, F140; the old AdvisorTab's `filtered`). Pure.
 *
 * Every figure is the server's: the monthly total (`premium.monthly`), the change against what each plan replaces
 * (`change.pct`, F18), the numbers parsed once in `facts.numbers` (sliders, caps and number rules; F21) and the facts
 * (incomplete, compliance, open warnings). This only compares them with what was typed; it never prices a plan (§3.9).
 * A blank never meets a filter. A plan with no total yet is never hidden silently: under the budget or a total rule
 * it is named (`unpriced`, "N have no price yet — enter enrollment", F140), and a priced plan with nothing to compare
 * with under the budget likewise (`uncompared`).
 *
 * The config is the board's one object (boardConfig.js; quotes/board.py cleans it). Filters carry across lines,
 * except a rule that names a line (F27), and a rule on a column this line lacks rests (F24).
 */

import { TOTAL } from './boardConfig';

const STEP = 50;

/** The rules on `line`: `applied` filter here, `resting` name a column the line lacks; `totalCap` is the line's
 *  "Monthly total ≤ $" (the rule {total, <=, line}); rules naming another line are not shown here. */
export function lineRules(config, line, lineKeys) {
  const applied = [];
  const resting = [];
  let totalCap = null;
  for (const rule of config.rules ?? []) {
    if (rule.line && rule.line !== line) continue;
    if (rule.key === TOTAL && rule.op === '<=' && rule.line === line && !totalCap) {
      totalCap = rule;
      applied.push(rule);
    } else if (rule.key === TOTAL || lineKeys.has(rule.key)) applied.push(rule);
    else resting.push(rule);
  }
  return { applied, resting, totalCap };
}

function numberOf(plan, key) {
  const value = key === TOTAL ? plan.premium?.monthly : plan.facts?.numbers?.[key];
  return typeof value === 'number' ? value : null;
}

const COMPARE = {
  '<': (a, b) => a < b,
  '<=': (a, b) => a <= b,
  '>': (a, b) => a > b,
  '>=': (a, b) => a >= b,
  '=': (a, b) => a === b,
};

/** Does a plan meet one rule? A number rule reads the server's number; a text rule matches a phrase, any case. */
export function ruleMet(plan, rule) {
  if (rule.op === 'contains' || rule.op === 'excludes') {
    const text = String(plan.values?.[rule.key] ?? '').trim().toLowerCase();
    if (!text) return false;
    const has = text.includes(String(rule.value).toLowerCase());
    return rule.op === 'contains' ? has : !has;
  }
  const value = numberOf(plan, rule.key);
  return value !== null && Boolean(COMPARE[rule.op]?.(value, Number(rule.value)));
}

/** The line's sliders with their bounds: [{key, label, op, value, bounds: {min, max} | null}], in steps of 50 bounded
 *  by the line's quotes (F20); no bounds when fewer than two values differ. */
export function lineSliders(defs, quotes, config) {
  return defs.map((def) => {
    const values = quotes.map((plan) => numberOf(plan, def.key)).filter((v) => v !== null);
    const low = Math.min(...values);
    const high = Math.max(...values);
    const bounds = values.length && low !== high ? { min: Math.floor(low / STEP) * STEP, max: Math.ceil(high / STEP) * STEP } : null;
    return { ...def, value: config.sliders?.[def.key] ?? null, bounds };
  });
}

/** Each check, with its words for the reasons a plan is hidden. */
function failures(plan, ctx) {
  const { config, finder, rules, sliders, caps } = ctx;
  const out = [];
  if (finder?.active && !finder.ids.has(plan.id)) out.push('find');
  const monthly = plan.premium?.monthly ?? null;
  if (config.budget_pct != null) {
    const pct = plan.change?.pct;
    if (typeof pct !== 'number' || pct > config.budget_pct) out.push(monthly === null ? 'price' : pct == null ? 'compare' : 'budget');
  }
  for (const rule of rules) {
    if (!ruleMet(plan, rule)) out.push(rule.key === TOTAL && monthly === null ? 'price' : 'rule');
  }
  for (const slider of sliders) {
    if (slider.value == null) continue;
    const value = numberOf(plan, slider.key);
    if (value === null || !COMPARE[slider.op](value, slider.value)) out.push('slider');
  }
  for (const cap of caps) {
    const limit = config[cap.key];
    if (limit == null) continue;
    const value = numberOf(plan, cap.field);
    if (value === null || value > limit) out.push('cap');
  }
  const hide = new Set(config.hide ?? []);
  if (hide.has('incomplete') && plan.facts?.incomplete) out.push('incomplete');
  if (hide.has('noncompliant') && plan.facts?.compliance?.length) out.push('noncompliant');
  if (config.starred_only && !plan.starred) out.push('starred');
  if (config.needs_check && !Object.values(plan.cells ?? {}).some((cell) => cell.m === 'check')) out.push('check');
  if (config.to_review && !plan.facts?.flags) out.push('review');
  if (config.carriers?.length && !config.carriers.includes(plan.carrier)) out.push('carrier');
  return out;
}

/**
 * The quotes the config shows, in the order given: {shown, unpriced, uncompared}. `unpriced` are the plans hidden
 * only because they have no total yet (budget or total rule); `uncompared` the priced ones the budget hides only
 * because nothing gives them a change.
 */
export function filterQuotes(quotes, ctx) {
  const shown = [];
  const unpriced = [];
  const uncompared = [];
  for (const plan of quotes) {
    const failed = failures(plan, ctx);
    if (!failed.length) shown.push(plan);
    else if (failed.every((why) => why === 'price')) unpriced.push(plan);
    else if (failed.every((why) => why === 'compare')) uncompared.push(plan);
  }
  return { shown, unpriced, uncompared };
}

/** "N active" (F26): the triggers set that this line shows — each rule here (applied or resting) counts one. */
export function activeCount(config, { rules, sliders, caps }) {
  return [
    Boolean(config.find?.trim()),
    config.budget_pct != null,
    ...sliders.map((slider) => slider.value != null),
    ...caps.map((cap) => config[cap.key] != null),
    ...(config.hide ?? []).map(() => true),
    config.starred_only,
    config.needs_check,
    config.to_review,
    (config.carriers ?? []).length > 0,
  ].filter(Boolean).length + rules.applied.length + rules.resting.length;
}

/** The carriers a chip row offers (F23): the line's quote carriers, sorted, shown with two or more. */
export function quoteCarriers(quotes) {
  return [...new Set(quotes.map((plan) => plan.carrier).filter(Boolean))].sort((a, b) => a.localeCompare(b));
}
