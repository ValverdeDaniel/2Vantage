import { describe, expect, it } from 'vitest';
import { bands, boardColumns, cents, money, settingsFrom, termText, toggleLaser, withoutParam } from './stopLossModel';

const column = (id, extra = {}) => ({ id, carrier: `C${id}`, name: `P${id}`, scored: true, terms: {}, ...extra });
const data = {
  currents: [1],
  columns: [column(1, { current: true }), column(2), column(3, { scored: false }), column(4)],
  ranks: { max_annual_liability: [4, 2, 3], annual_premium: [2, 3, 4] },
};

describe('F104 the laser what-if is the read’s parameter, never stored', () => {
  it('ticks lasers off and back on by position, and writes them as plan:position pairs', () => {
    let dropped = toggleLaser({}, 12, 2);
    dropped = toggleLaser(dropped, 7, 1);
    dropped = toggleLaser(dropped, 12, 1);
    expect(withoutParam(dropped)).toBe('7:1,12:1,12:2');
    dropped = toggleLaser(toggleLaser(dropped, 7, 1), 12, 2);
    expect(dropped).toEqual({ 12: [1] });
    expect(withoutParam({})).toBe('');
  });
});

describe('F100 the board’s columns follow the server’s ranking', () => {
  it('puts the in-force contract first, then the options lowest first, the unscored ones hidden on request', () => {
    const shown = boardColumns(data, 'max_annual_liability', false);
    expect(shown.columns.map((c) => c.id)).toEqual([1, 4, 2, 3]);
    expect(shown.best.id).toBe(4);
    expect(boardColumns(data, 'max_annual_liability', true).options.map((c) => c.id)).toEqual([4, 2]);
    expect(boardColumns(data, 'annual_premium', false).best.id).toBe(2);
  });
});

describe('F102 F103 the option table and the saved settings', () => {
  it('shows the PEPM rows only outside Annual only', () => {
    const keys = (annual) => bands(annual).flatMap(([, rows]) => rows.map((row) => row.key));
    expect(keys(false)).toContain('spec_rate');
    expect(keys(true)).not.toContain('spec_rate');
    expect(keys(true)).toContain('annual_premium');
  });

  it('reads a figure the server could not state as a dash, and applies a saved setting over the defaults', () => {
    expect(money(null)).toBe('—');
    expect(money(804933)).toBe('$804,933');
    expect(cents(97.3)).toBe('$97.30');
    const defaults = { rank_by: 'max_annual_liability', annual_mode: false, show_terms: true, hide_unscored: false };
    expect(settingsFrom(defaults, { annual_mode: true })).toEqual({ ...defaults, annual_mode: true });
    expect(settingsFrom(defaults, {})).toEqual(defaults);
  });

  it('formats a term by its field type', () => {
    const fields = { sl_collateral: { key: 'sl_collateral', type: 'amount' } };
    expect(termText(fields, 'sl_collateral', column(1, { terms: { sl_collateral: '1500' } }))).toBe('$1,500');
    expect(termText(fields, 'sl_tlo', column(1))).toBe('—');
  });
});
