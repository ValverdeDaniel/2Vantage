import { describe, expect, it } from 'vitest';
import { defaultConfig, setTotalCap } from './boardConfig';
import { activeCount, filterQuotes, lineRules, lineSliders, quoteCarriers, ruleMet } from './filter';

// Quotes as the comparison sends them: the server's monthly total, change and numbers. Synthetic.
function quote(id, monthly, pct, extra = {}) {
  return {
    id,
    carrier: extra.carrier ?? 'Cigna',
    name: `Plan ${id}`,
    starred: Boolean(extra.starred),
    values: extra.values ?? {},
    cells: extra.cells ?? {},
    premium: { monthly, reason: monthly === null ? 'no_enrollment' : null, reason_words: monthly === null ? 'enter enrollment' : null },
    change: pct === undefined ? null : { pct },
    facts: { incomplete: false, flags: 0, compliance: [], numbers: {}, ...extra.facts },
  };
}

const MEDICAL = new Set(['deductible_single', 'oop_max_single', 'rate_ee', 'pcp_copay', 'diagnostic_test']);
const SLIDERS = [
  { key: 'deductible_single', label: 'Max deductible', op: '<=' },
  { key: 'oop_max_single', label: 'Max OOP', op: '<=' },
];
const CAPS = [
  { key: 'ee_rate_max', field: 'rate_ee' },
  { key: 'copay_max', field: 'pcp_copay' },
];

function run(quotes, patch, finder = null, line = 'medical') {
  const config = { ...defaultConfig(), ...patch };
  const rules = lineRules(config, line, MEDICAL);
  const sliders = lineSliders(SLIDERS, quotes, config);
  return filterQuotes(quotes, { config, finder, rules: rules.applied, sliders, caps: CAPS });
}
const ids = (plans) => plans.map((plan) => plan.id);

describe('Monthly total ≤ $ (F19, F140)', () => {
  const quotes = [quote(1, 17743, -2.8), quote(2, 27200, -1.6), quote(3, null), quote(4, 45000, 1)];

  it('hides the dearer plans and names those with no total, never hiding them silently', () => {
    const answer = run(quotes, setTotalCap(defaultConfig(), 'medical', '45000'));
    expect(ids(answer.shown)).toEqual([1, 2, 4]);
    expect(ids(answer.unpriced)).toEqual([3]);
    expect(answer.unpriced[0].premium.reason_words).toBe('enter enrollment');
    expect(ids(run(quotes, setTotalCap(defaultConfig(), 'medical', '20000')).shown)).toEqual([1]);
  });

  it("is kept per line: another line's cap does not filter here (F27)", () => {
    const config = setTotalCap(defaultConfig(), 'dental', '100');
    expect(ids(run(quotes, config).shown)).toEqual([1, 2, 3, 4]);
    expect(lineRules(config, 'dental', new Set()).totalCap.value).toBe(100);
  });

  it('a blank cap removes the rule', () => {
    const config = setTotalCap(setTotalCap(defaultConfig(), 'medical', '45000'), 'medical', '');
    expect(config.rules).toEqual([]);
  });
});

describe('the budget select (F18)', () => {
  const quotes = [quote(1, 100, 4.9), quote(2, 100, 5.1), quote(3, 100, -12), quote(4, null), quote(5, 100)];

  it("tests the server's change against what each plan replaces", () => {
    expect(ids(run(quotes, { budget_pct: 5 }).shown)).toEqual([1, 3]);
    expect(ids(run(quotes, { budget_pct: -10 }).shown)).toEqual([3]);
  });

  it('names the plans with no price and those with nothing to compare with', () => {
    const answer = run(quotes, { budget_pct: 5 });
    expect(ids(answer.unpriced)).toEqual([4]);
    expect(ids(answer.uncompared)).toEqual([5]);
  });

  it('a plan hidden by something else as well is not named', () => {
    const finder = { active: true, ids: new Set([1]) };
    expect(run(quotes, { budget_pct: 5 }, finder).unpriced).toEqual([]);
  });
});

describe('sliders, caps, hides and switches (F20–F23)', () => {
  const quotes = [
    quote(1, 100, 0, { facts: { numbers: { deductible_single: 1000, rate_ee: 512.34, pcp_copay: 20 } } }),
    quote(2, 100, 0, { facts: { numbers: { deductible_single: 3375, rate_ee: 640 }, incomplete: true } }),
    quote(3, 100, 0, { carrier: 'UnitedHealthcare', starred: true, facts: { numbers: {}, compliance: ['minimum_value'], flags: 2 } }),
    quote(4, 100, 0, { cells: { rate_ee: { m: 'check' } }, facts: { numbers: { deductible_single: 6000 } } }),
  ];

  it('sliders move in steps of 50 between the quotes\' lowest and highest values', () => {
    const [deductible, oop] = lineSliders(SLIDERS, quotes, defaultConfig());
    expect(deductible.bounds).toEqual({ min: 1000, max: 6000 });
    expect(oop.bounds).toBeNull(); // no data: nothing to slide
    expect(lineSliders(SLIDERS, [quotes[0]], defaultConfig())[0].bounds).toBeNull(); // one value
    expect(lineSliders(SLIDERS, [quotes[0], quotes[1]], defaultConfig())[0].bounds).toEqual({ min: 1000, max: 3400 });
  });

  it('a slider or a cap hides a plan whose value is blank or above it', () => {
    expect(ids(run(quotes, { sliders: { deductible_single: 3400 } }).shown)).toEqual([1, 2]);
    expect(ids(run(quotes, { ee_rate_max: 600 }).shown)).toEqual([1]);
    expect(ids(run(quotes, { copay_max: 25 }).shown)).toEqual([1]);
  });

  it('hides and switches use the server\'s facts', () => {
    expect(ids(run(quotes, { hide: ['incomplete'] }).shown)).toEqual([1, 3, 4]);
    expect(ids(run(quotes, { hide: ['noncompliant'] }).shown)).toEqual([1, 2, 4]);
    expect(ids(run(quotes, { starred_only: true }).shown)).toEqual([3]);
    expect(ids(run(quotes, { needs_check: true }).shown)).toEqual([4]);
    expect(ids(run(quotes, { to_review: true }).shown)).toEqual([3]);
    expect(ids(run(quotes, { carriers: ['UnitedHealthcare'] }).shown)).toEqual([3]);
    expect(quoteCarriers(quotes)).toEqual(['Cigna', 'UnitedHealthcare']);
  });
});

describe("Claude's rules (F24)", () => {
  it('a number rule reads the server\'s number; a blank never meets it', () => {
    const plan = quote(1, 100, 0, { facts: { numbers: { deductible_single: 1500 } } });
    expect(ruleMet(plan, { key: 'deductible_single', op: '<', value: 2000 })).toBe(true);
    expect(ruleMet(plan, { key: 'oop_max_single', op: '<', value: 2000 })).toBe(false);
    expect(ruleMet(plan, { key: 'total', op: '>=', value: 100 })).toBe(true);
  });

  it('a text rule matches a phrase, any case', () => {
    const plan = quote(1, 100, 0, { values: { diagnostic_test: 'Deductible, then 20%' } });
    expect(ruleMet(plan, { key: 'diagnostic_test', op: 'contains', value: 'DEDUCTIBLE' })).toBe(true);
    expect(ruleMet(plan, { key: 'diagnostic_test', op: 'excludes', value: 'not covered' })).toBe(true);
    expect(ruleMet(quote(2, 100, 0), { key: 'diagnostic_test', op: 'excludes', value: 'x' })).toBe(false);
  });

  it('a rule on a column the line lacks rests; one naming another line is not shown', () => {
    const config = {
      ...defaultConfig(),
      rules: [
        { key: 'den_annual_max', op: '>=', value: 1500 },
        { key: 'deductible_single', op: '<', value: 2000 },
        { key: 'total', op: '<=', value: 9, line: 'dental' },
      ],
    };
    const rules = lineRules(config, 'medical', MEDICAL);
    expect(rules.applied.map((r) => r.key)).toEqual(['deductible_single']);
    expect(rules.resting.map((r) => r.key)).toEqual(['den_annual_max']);
  });
});

describe('N active (F26)', () => {
  it('counts what is set on this line, each rule here one', () => {
    const config = { ...setTotalCap(defaultConfig(), 'medical', 45000), find: 'uhc', hide: ['incomplete'], ee_rate_max: 600 };
    const rules = lineRules(config, 'medical', MEDICAL);
    const sliders = lineSliders(SLIDERS, [], config);
    expect(activeCount(config, { rules, sliders, caps: CAPS })).toBe(4);
    expect(activeCount(defaultConfig(), { rules: lineRules(defaultConfig(), 'medical', MEDICAL), sliders, caps: CAPS })).toBe(0);
  });
});
