import { describe, expect, it } from 'vitest';
import { clearFilters, defaultConfig, fromSaved, readConfig, removeRule, setTotalCap, writeConfig } from './boardConfig';

// The slice of /api/meta/ board the config reads (quotes/board_presets.py).
const BOARD = {
  default_preset: 'primary',
  default_sort: 'proposal',
  presets: [{ key: 'primary' }, { key: 'rates' }],
  budget: [{ value: null }, { value: 5 }, { value: -10 }],
  hides: [{ key: 'incomplete' }, { key: 'noncompliant' }],
  rule_ops: [
    { key: '<=', kind: 'number' },
    { key: 'contains', kind: 'text' },
  ],
};

describe('the board config in the URL (§3.9)', () => {
  it('a config goes to the URL and comes back the same', () => {
    const config = {
      ...setTotalCap(defaultConfig(BOARD), 'medical', 45000),
      find: 'UHC hdhp',
      budget_pct: -10,
      sliders: { deductible_single: 3000 },
      ee_rate_max: 600,
      hide: ['incomplete', 'noncompliant'],
      starred_only: true,
      to_review: true,
      carriers: ['Cigna', 'Florida Blue'],
      preset: 'rates',
      sort: { key: 'total', dir: -1 },
    };
    config.rules.push({ key: 'diagnostic_test', op: 'contains', value: 'a~b c' });
    const params = writeConfig(new URLSearchParams('line=medical&view=quotes'), config, BOARD);
    expect(params.get('line')).toBe('medical'); // other parameters are kept
    expect(params.getAll('rule')).toEqual(['total~<=~medical~45000', 'diagnostic_test~contains~~a~b c']);
    expect(readConfig(params, BOARD)).toEqual({ ...config, layout: 'rows' });
  });

  it('the defaults write nothing', () => {
    expect(writeConfig(new URLSearchParams('line=dental'), defaultConfig(BOARD), BOARD).toString()).toBe('line=dental');
  });

  it('a hand-edited URL never breaks the board: what cannot be read is the default', () => {
    const params = new URLSearchParams('budget=12&ee=cheap&hide=sold,incomplete&rule=total~<<~~9&rule=total~<=~~x&preset=all9');
    const config = readConfig(params, BOARD);
    expect(config.budget_pct).toBeNull();
    expect(config.ee_rate_max).toBeNull();
    expect(config.hide).toEqual(['incomplete']);
    expect(config.rules).toEqual([]);
    expect(config.preset).toBe('primary');
  });
});

describe('Clear, the total cap, rule chips and saved setups (F19, F24, F26, F28)', () => {
  it('Clear turns every filter off and keeps the columns, the order and the layout', () => {
    const config = { ...defaultConfig(BOARD), find: 'x', budget_pct: 5, preset: 'rates', sort: { key: 'total', dir: -1 }, layout: 'cols' };
    expect(clearFilters(config, BOARD)).toEqual({ ...defaultConfig(BOARD), preset: 'rates', sort: { key: 'total', dir: -1 }, layout: 'cols' });
  });

  it('the total cap replaces its own line\'s rule only', () => {
    let config = setTotalCap(defaultConfig(BOARD), 'medical', 45000);
    config = setTotalCap(config, 'dental', 3000);
    config = setTotalCap(config, 'medical', 40000);
    expect(config.rules).toEqual([
      { key: 'total', op: '<=', value: 3000, line: 'dental' },
      { key: 'total', op: '<=', value: 40000, line: 'medical' },
    ]);
  });

  it('a chip removes its own rule', () => {
    const config = { ...defaultConfig(BOARD), rules: [{ key: 'deductible_single', op: '<=', value: 2000 }, { key: 'total', op: '<=', value: 9 }] };
    expect(removeRule(config, { key: 'total', op: '<=', value: 9 }).rules).toEqual([{ key: 'deductible_single', op: '<=', value: 2000 }]);
  });

  it('a saved setup applies whole: what it does not name is off', () => {
    const now = { ...defaultConfig(BOARD), find: 'aetna', starred_only: true };
    const applied = fromSaved({ find: 'UHC', preset: 'rates', unknown: 1 }, BOARD, 'cols');
    expect(applied).toEqual({ ...defaultConfig(BOARD), find: 'UHC', preset: 'rates', layout: 'cols' });
    expect(applied.starred_only).toBe(false);
    expect(now.starred_only).toBe(true);
  });
});
