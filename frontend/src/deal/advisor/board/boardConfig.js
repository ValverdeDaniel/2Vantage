/*
 * The board's config (plan.md §6.7, §3.9; F14–F28, F31–F34): one object holds the finder's words, the filters, the
 * columns preset, the sort and the layout. A saved setup stores it whole and applies it whole; Claude's `set_board`
 * (slice 24) patches it; quotes/board.py `clean_config` is its server half and refuses any other key. Pure.
 *
 * In-tab state lives in the query string (§3.9): every setting but the layout (kept per browser with ⇄ Transpose,
 * F34) is a URL parameter, written only when it differs from the default, so a link or a reload shows the same board.
 * A hand-edited URL never breaks the board: a value it cannot read is the default.
 *   find=UHC · budget=-10 · rule=total~<=~medical~45000 (key~op~line~value) · slider=deductible_single:3000 ·
 *   ee=600 · copay=30 · hide=incomplete,noncompliant · starred=1 · check=1 · review=1 · carrier=Cigna ·
 *   preset=rates · sort=-total
 */

export const TOTAL = 'total';
const FLAGS = { starred_only: 'starred', needs_check: 'check', to_review: 'review' };
const AMOUNTS = { ee_rate_max: 'ee', copay_max: 'copay' };
export const BOARD_PARAMS = ['find', 'budget', 'rule', 'slider', 'ee', 'copay', 'hide', 'starred', 'check', 'review',
  'carrier', 'preset', 'sort']; // prettier-ignore

/** The config with nothing set, from meta's board lists. */
export function defaultConfig(board = {}) {
  return {
    find: '',
    budget_pct: null,
    rules: [],
    sliders: {},
    ee_rate_max: null,
    copay_max: null,
    hide: [],
    starred_only: false,
    needs_check: false,
    to_review: false,
    carriers: [],
    preset: board.default_preset ?? 'primary',
    sort: { key: board.default_sort ?? 'proposal', dir: 1 },
    layout: 'rows',
  };
}

/** A typed dollar amount: '' → null; a finite number at or above 0, or null when it is not one. */
export function amountOf(text) {
  if (text == null || String(text).trim() === '') return null;
  const n = Number(text);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

function readRule(text, ops) {
  const [key, op, line, ...rest] = String(text).split('~');
  const raw = rest.join('~');
  const kind = ops.get(op);
  if (!key || !kind || raw === '') return null;
  const value = kind === 'number' ? Number(raw) : raw;
  if (kind === 'number' && !Number.isFinite(value)) return null;
  return line ? { key, op, value, line } : { key, op, value };
}

/** The config the URL holds; `layout` is the kept one. */
export function readConfig(params, board = {}, layout = 'rows') {
  const config = { ...defaultConfig(board), layout };
  const ops = new Map((board.rule_ops ?? []).map((op) => [op.key, op.kind]));
  config.find = params.get('find') ?? '';
  const budget = Number(params.get('budget'));
  if ((board.budget ?? []).some((rung) => rung.value !== null && rung.value === budget)) config.budget_pct = budget;
  config.rules = params.getAll('rule').map((text) => readRule(text, ops)).filter(Boolean);
  for (const text of params.getAll('slider')) {
    const [key, value] = text.split(':');
    if (key && amountOf(value) !== null) config.sliders[key] = amountOf(value);
  }
  for (const [key, name] of Object.entries(AMOUNTS)) config[key] = amountOf(params.get(name));
  const hides = new Set((params.get('hide') ?? '').split(','));
  config.hide = (board.hides ?? []).map((hide) => hide.key).filter((key) => hides.has(key));
  for (const [key, name] of Object.entries(FLAGS)) config[key] = params.get(name) === '1';
  config.carriers = [...new Set(params.getAll('carrier').filter(Boolean))];
  const preset = params.get('preset');
  if ((board.presets ?? []).some((p) => p.key === preset)) config.preset = preset;
  const sort = params.get('sort');
  if (sort) config.sort = sort.startsWith('-') ? { key: sort.slice(1), dir: -1 } : { key: sort, dir: 1 };
  return config;
}

/** `params` with the board's parameters replaced by `config`'s (only what differs from the default); others kept. */
export function writeConfig(params, config, board = {}) {
  const next = new URLSearchParams(params);
  for (const name of BOARD_PARAMS) next.delete(name);
  const base = defaultConfig(board);
  if (config.find) next.set('find', config.find);
  if (config.budget_pct != null) next.set('budget', String(config.budget_pct));
  for (const rule of config.rules ?? []) next.append('rule', [rule.key, rule.op, rule.line ?? '', rule.value].join('~'));
  for (const [key, value] of Object.entries(config.sliders ?? {})) if (value != null) next.append('slider', `${key}:${value}`);
  for (const [key, name] of Object.entries(AMOUNTS)) if (config[key] != null) next.set(name, String(config[key]));
  if (config.hide?.length) next.set('hide', config.hide.join(','));
  for (const [key, name] of Object.entries(FLAGS)) if (config[key]) next.set(name, '1');
  for (const carrier of config.carriers ?? []) next.append('carrier', carrier);
  if (config.preset && config.preset !== base.preset) next.set('preset', config.preset);
  const sort = config.sort ?? base.sort;
  if (sort.key !== base.sort.key || sort.dir !== base.sort.dir) next.set('sort', `${sort.dir === -1 ? '-' : ''}${sort.key}`);
  return next;
}

/** Clear (F26): every filter off; the columns, the order and the layout stay. */
export function clearFilters(config, board = {}) {
  const base = defaultConfig(board);
  return { ...base, preset: config.preset, sort: config.sort, layout: config.layout };
}

/** "Monthly total ≤ $" on `line` (F19): the rule {total, <=, value, line}, replaced or (blank) removed. */
export function setTotalCap(config, line, value) {
  const rules = (config.rules ?? []).filter((rule) => !(rule.key === TOTAL && rule.op === '<=' && rule.line === line));
  const cap = amountOf(value);
  return { ...config, rules: cap === null ? rules : [...rules, { key: TOTAL, op: '<=', value: cap, line }] };
}

/** A rule chip's ✕ (F24): the user can only remove Claude's rules. */
export function removeRule(config, rule) {
  const same = (r) => r.key === rule.key && r.op === rule.op && r.value === rule.value && (r.line ?? '') === (rule.line ?? '');
  return { ...config, rules: (config.rules ?? []).filter((r) => !same(r)) };
}

/** A saved setup applied (F28): its config over the defaults, so anything it does not name is off. */
export function fromSaved(saved, board = {}, layout = 'rows') {
  const base = { ...defaultConfig(board), layout };
  const known = Object.fromEntries(Object.entries(saved ?? {}).filter(([key]) => key in base));
  return { ...base, ...known, sliders: { ...(known.sliders ?? {}) } };
}
