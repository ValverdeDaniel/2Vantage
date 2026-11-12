import { describe, expect, it } from 'vitest';
import { bannerTail, controlsOf, isCollapsed, meterOf, rememberCollapsed, statusOf, subtitleOf } from './checklistModel';

const row = (changes = {}) => ({
  key: 'renewal',
  satisfy: 'document',
  status: 'missing',
  done: false,
  waived: false,
  auto_waived: false,
  forced: false,
  optional: false,
  ...changes,
});

describe('B27 the meter', () => {
  it('colours green when clear, amber from 60 %, else rose', () => {
    expect(meterOf({ required: 6, done: 6, all_clear: true })).toEqual({ done: 6, required: 6, pct: 100, cls: 'bb-green' });
    expect(meterOf({ required: 5, done: 3 }).cls).toBe('bb-amber');
    expect(meterOf({ required: 6, done: 1 }).cls).toBe('bb-rose');
    expect(meterOf({ required: 0, done: 0, all_clear: true }).pct).toBe(100);
  });
});

describe('B27 a row', () => {
  it('reads Not needed, Waived, Optional, Re-asked, ✓ or Missing', () => {
    expect(statusOf(row({ auto_waived: true, waived: true })).text).toBe('Not needed');
    expect(statusOf(row({ waived: true })).text).toBe('Waived');
    expect(statusOf(row({ status: 'offer', optional: true })).text).toBe('Optional');
    expect(statusOf(row({ forced: true })).text).toBe('Re-asked');
    expect(statusOf(row({ done: true }))).toEqual({ check: true });
    expect(statusOf(row())).toEqual({ text: 'Missing', cls: 'bb-badge-rose' });
  });

  it('offers Attach and On file on a document, Confirmed on an attested item', () => {
    expect(controlsOf(row())).toEqual({ attach: true, tick: 'On file', override: 'notNeeded' });
    expect(controlsOf(row({ key: 'cobra', satisfy: 'attest' }))).toEqual({ attach: false, tick: 'Confirmed', override: 'notNeeded' });
  });

  it('offers Still needed on a done row and Undo once a person waived or re-asked it', () => {
    expect(controlsOf(row({ done: true })).override).toBe('still');
    expect(controlsOf(row({ waived: true }))).toEqual({ attach: false, tick: null, override: 'undo' });
    expect(controlsOf(row({ forced: true })).override).toBe('undo');
  });

  it('offers nothing to override on the derived items, an offer, or a row Not needed on its own', () => {
    expect(controlsOf(row({ key: 'census', satisfy: 'auto' }))).toEqual({ attach: false, tick: null, override: null });
    expect(controlsOf(row({ key: 'stop_loss_disclosure', optional: true, status: 'offer' }))).toEqual({
      attach: false,
      tick: null,
      override: null,
    });
    expect(controlsOf(row({ auto_waived: true, waived: true })).override).toBe(null);
  });
});

describe('B25 the head', () => {
  it('says the tier, the enrolled count and where the deal stands', () => {
    const card = { tier_label: '51–99 enrolled', enrolled: 60 };
    expect(subtitleOf(card, null)).toBe('51–99 enrolled · 60 enrolled — what carriers need before we market.');
    expect(subtitleOf({ ...card, enrolled: null }, '2027-01-02')).toBe(
      '51–99 enrolled · — enrolled — what this group owed at market. Still editable.',
    );
    expect(subtitleOf({ ...card, estimate: true }, null)).toContain('60 enrolled (estimate)');
  });
});

describe('B9 the banner', () => {
  it('adds HR contact, Signed BOR and Census in the old order', () => {
    expect(bannerTail({ contacts_ok: false, bor_on_file: false, census_ok: false })).toBe(' · HR contact · Signed BOR · Census');
    expect(bannerTail({ contacts_ok: true, bor_on_file: true, census_ok: true })).toBe('');
  });
});

describe('B27 the remembered collapse', () => {
  it('keeps an entry only for a card put away', () => {
    const store = new Map();
    const storage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) };
    expect(isCollapsed(storage, 7)).toBe(false);
    rememberCollapsed(storage, 7, true);
    expect(isCollapsed(storage, 7)).toBe(true);
    rememberCollapsed(storage, 7, false);
    expect(store.get('vantage.bnf.checklist')).toBe('{}');
  });
});
