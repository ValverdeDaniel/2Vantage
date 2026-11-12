/*
 * The board as the tables draw it (plan.md §8.14; F9, F31–F33, F41, F57): one line's comparison, the preset and the
 * sort, turned into columns, the quotes in the sort's order and the count line's words. Pure; every figure is the
 * server's (premium, change, closeness): this only orders and words them.
 */

import { formatMoney } from '../../../lib/format';
import { sortBy } from '../../../grid/sort';
import { boardColumns, fieldsByKey } from './boardColumns';
import { lineOrder } from './boardOrder';

const NUMERIC = ['amount', 'percent', 'rate', 'rate4', 'number'];

/** A stored value as a number ('$3,300' → 3300), or null when it is not one plain number. */
export function numberOf(raw) {
  const text = String(raw ?? '').trim().replace(/[$,%\s]/g, '');
  if (!/^-?\d+(\.\d+)?$/.test(text)) return null;
  return Number(text);
}

/** "Open Access · HDHP": a plan's network and type (the derived Network / type column). */
export function networkType(plan) {
  return [plan.values?.network, plan.values?.plan_type].map((v) => String(v ?? '').trim()).filter(Boolean).join(' · ');
}

/** What a column sorts a plan by (F32): the server's figures for derived columns, the value for a field. */
export function sortValue(key, plan, fields, rank) {
  switch (key) {
    case 'proposal':
      return rank.get(plan.id);
    case 'closest':
      return plan.closeness;
    case 'star':
      return plan.starred ? 0 : 1;
    case 'carrier':
      return `${plan.carrier} ${plan.name}`.toLowerCase();
    case 'total':
      return plan.premium?.monthly ?? null;
    case 'delta':
      return plan.change?.pct ?? null;
    case 'network_type':
      return networkType(plan).toLowerCase();
    default: {
      const raw = plan.values?.[key];
      if (NUMERIC.includes(fields[key]?.type)) return numberOf(raw);
      return String(raw ?? '').toLowerCase();
    }
  }
}

/**
 * {plans, order, currents, quotes, sorted, columns, inProposal, fields}: `quotes` are the line's plans that are not
 * current (the ones a sort orders and a tick may take in every mode); `sorted` is them in the sort's order — the
 * server's own order for Proposal order, so a typed value never moves a plan there.
 */
export function buildBoard({ comparison, meta, line, preset, sort }) {
  const plans = comparison.plans;
  const order = lineOrder(plans);
  const fields = fieldsByKey(meta);
  const quotes = plans.filter((plan) => plan.role !== 'current');
  const inProposal = sort.key === 'proposal';
  const sorted = inProposal ? quotes : sortBy(quotes, (plan) => sortValue(sort.key, plan, fields, order.rank), sort.dir);
  return {
    line, // the board's line: what a plan's ⋯ menu offers depends on it (Attach SBC…, medical only; slice 22)
    plans,
    order,
    currents: order.currents,
    quotes,
    sorted,
    inProposal,
    fields,
    columns: boardColumns(meta, line, preset, sort.key),
  };
}

/**
 * The count line (F9): "Showing N of M quoted plans · K shortlisted · current plan (Aetna) $18,251/mo", where K
 * counts this line only and $X is the Current package's total; then a note for several or no current plans.
 */
export function countLine({ shown, quotes, currents, packages = [] }) {
  const starred = quotes.filter((plan) => plan.starred).length;
  const total = packages.find((pkg) => pkg.key === 'current')?.monthly ?? null;
  const parts = [`Showing ${shown} of ${quotes.length} quoted plan${quotes.length === 1 ? '' : 's'}`];
  if (starred) parts.push(`${starred} shortlisted`);
  if (currents.length === 1) {
    parts.push(`current plan (${currents[0].carrier})${total != null ? ` ${formatMoney(total)}/mo` : ''}`);
  } else if (currents.length > 1) {
    const sum = total != null ? ` ${formatMoney(total)}/mo` : '';
    parts.push(`${currents.length} current plans${sum} — link each starred quote to the plan it replaces`);
  } else {
    parts.push('no current plan set — Δ% is unavailable');
  }
  return parts.join(' · ');
}

/** ⇄ Transpose (F34): refused above `max` plans on screen (meta board.transpose_max), the kept choice kept for later. */
export function transposeState(count, max, kept) {
  const blocked = count > max;
  return { blocked, shown: blocked ? 'rows' : kept === 'cols' ? 'cols' : 'rows' };
}
