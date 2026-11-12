/*
 * The stop-loss board's pure helpers (plan.md §8.14; F98–F105; the old StopLossAnalysis.jsx at 891f1b3): the laser
 * what-if as the read's `without` parameter, the board's columns in order, the option table's rows, and how a figure
 * reads. Every figure is the server's, already rounded in quotes' math; nothing here computes money (rule 5).
 */
import { formatMoney, formatRate } from '../../../lib/format';
import { displayValue } from '../../../lib/fieldValue';

/** Whole dollars, or '—' when the server could not state the figure. */
export const money = (value) => (value == null ? '—' : formatMoney(value));
/** PEPM money to the cent, or '—'. */
export const cents = (value) => (value == null ? '—' : formatRate(value));
/** A count or a factor as stated, or '—'. */
export const plain = (value) => (value == null || value === '' ? '—' : String(value));

/** The what-if as the read's `without`: "12:1,12:3,15:2" (plan id : laser position), sorted, '' when nothing. */
export function withoutParam(dropped) {
  return Object.entries(dropped)
    .flatMap(([planId, positions]) => [...positions].map((n) => [Number(planId), Number(n)]))
    .sort((a, b) => a[0] - b[0] || a[1] - b[1])
    .map(([planId, n]) => `${planId}:${n}`)
    .join(',');
}

/** The what-if with one laser ticked off (or back on). Never stored: it lives as long as the board is on screen. */
export function toggleLaser(dropped, planId, n) {
  const mine = new Set(dropped[planId] ?? []);
  if (mine.has(n)) mine.delete(n);
  else mine.add(n);
  const next = { ...dropped, [planId]: [...mine] };
  if (!mine.size) delete next[planId];
  return next;
}

/**
 * The board's columns: every in-force contract in slot order, then the options in the server's ranking on `rankBy`
 * (lowest first, the ones it cannot score last), less the unscored ones when `hideUnscored`. `best` heads the ranking.
 */
export function boardColumns(data, rankBy, hideUnscored) {
  const byId = new Map(data.columns.map((column) => [column.id, column]));
  const currents = data.currents.map((id) => byId.get(id)).filter(Boolean);
  const ranked = (data.ranks[rankBy] ?? []).map((id) => byId.get(id)).filter(Boolean);
  const options = hideUnscored ? ranked.filter((column) => column.scored) : ranked;
  return { currents, options, columns: [...currents, ...options], best: options[0] ?? null };
}

const row = (label, key, show) => ({ label, key, show });

/** The option table's bands, in the workbook's own order (F103); `annual` shows the annual figures only. */
export function bands(annual) {
  return [
    annual
      ? ['PREMIUMS  (annual)', [row('Annual SL premium', 'annual_premium', money)]]
      : [
          'PREMIUMS  (annual = PEPM × headcount × months)',
          [
            row('Specific premium PEPM', 'spec_rate', cents),
            row('Aggregate premium PEPM', 'agg_rate', cents),
            row('TLO / other load PEPM', 'other_load', cents),
            row('Total SL premium PEPM', 'premium_pepm', cents),
            row('Annual SL premium', 'annual_premium', money),
          ],
        ],
    [
      'AGGREGATE ATTACHMENT',
      annual
        ? [
            row('Expected claims (annual)', 'annual_expected_claims', money),
            row('Annual aggregate attachment', 'annual_attachment', money),
          ]
        : [
            row('Expected claims factor PEPM', 'factor_pepm', cents),
            row('Aggregate corridor', 'corridor', plain),
            row('Min annual agg deductible (floor)', 'attachment_floor', money),
            row('Annual aggregate attachment', 'annual_attachment', money),
            row('Expected claims (annual)', 'annual_expected_claims', money),
          ],
    ],
    [
      'ADMIN & LASERS',
      [
        ...(annual ? [] : [row('Admin / TPA / network PEPM', 'admin_pepm', cents)]),
        row('Annual admin', 'annual_admin', money),
        row('Lasers above spec', 'laser_count', plain),
        row('Total additional laser liability', 'laser_liability', money),
      ],
    ],
  ];
}

/** The deltas against the one in-force contract, under the verdict row. */
export const DELTA_ROWS = [
  ['↳ Max liability vs current', 'max_annual_liability'],
  ['↳ Annual SL premium vs current', 'annual_premium'],
  ['↳ Laser liability vs current', 'laser_liability'],
];

/** A contract term as the board reads it, by its field's type (an amount as money), or '—'. */
export function termText(fields, key, column) {
  const raw = column.terms?.[key];
  if (raw == null || raw === '') return '—';
  return displayValue(fields[key], raw) || '—';
}

/** {field key: its meta entry}, for the terms. */
export function fieldsByKey(meta) {
  return Object.fromEntries((meta?.plans?.fields ?? []).map((field) => [field.key, field]));
}

/** The saved settings a saved setup carries back, over the defaults (F29). */
export function settingsFrom(defaults, config) {
  return { ...defaults, ...(config ?? {}) };
}

/** "Carrier · Plan" for a group row or a card. */
export function planWords(column) {
  return `${column.carrier || '—'}${column.name ? ` · ${column.name}` : ''}`;
}
