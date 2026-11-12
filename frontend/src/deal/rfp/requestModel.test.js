import { describe, expect, it } from 'vitest';
import { checklistDigest, isOpen, progress, shownCards } from './cardsModel';
import {
  adopt,
  bandWords,
  chipTitle,
  noCensusWords,
  optimistic,
  readinessClass,
  requestSummary,
  routeBody,
  toggleBody,
} from './requestModel';

const ROUTES = [
  { key: 'warner', long: 'Through Warner Pacific' },
  { key: 'direct', long: 'Direct to carriers' },
];
const FUNDING = ['fully_insured', 'level_funded', 'aso'];
const chip = (key, selected = false) => ({ key, selected, group: 'medical' });
const page = () => ({
  request: {
    route: 'direct',
    route_default: 'direct',
    route_stored: '',
    carriers: ['cigna'],
    funding: ['fully_insured', 'level_funded'],
    funding_default: true,
    other_carriers: '',
    due_date: null,
    notes: '',
  },
  carriers: [chip('aetna'), chip('cigna', true), chip('unum')],
  done: { request: { by: 'Dana', at: '2026-11-12T10:00:00Z' } },
});

describe('K28 the collapsed request card', () => {
  it('reads route · carriers · due date', () => {
    const request = { route: 'direct', carriers: ['a', 'b', 'c'], due_date: '2027-01-15' };
    expect(requestSummary(request, ROUTES)).toMatch(/^Direct to carriers · 3 carriers · due /);
    expect(requestSummary({ route: 'warner', carriers: ['a'] }, ROUTES)).toBe('Through Warner Pacific · 1 carrier');
  });
});

describe('K17 K18 the band line', () => {
  it('names the count, and where an estimate came from', () => {
    const large = { label: 'Large group (51+)', count: 60, estimate: false };
    expect(bandWords(large)).toBe('Large group (51+) · 60 enrolled');
    const estimate = { ...large, count: 120, estimate: true, from: "intake's eligible employees" };
    expect(bandWords(estimate)).toBe("Large group (51+) · 120 enrolled (an estimate: intake's eligible employees)");
    expect(bandWords({ label: 'Small group (2–50)', count: null })).toBe('Small group (2–50) · no enrolled count yet');
  });
});

describe('K8 the census line', () => {
  it('colours readiness green from 90, amber from 70, else rose', () => {
    expect([readinessClass(90), readinessClass(89), readinessClass(70), readinessClass(69)]).toEqual([
      'bb-green',
      'bb-amber',
      'bb-amber',
      'bb-rose',
    ]);
  });
  it('says where the band came from when there is no census', () => {
    const words = noCensusWords({ count: 52, from: 'the Advisor' });
    expect(words).toBe("no census yet — the band's 52 enrolled come from the Advisor");
    expect(noCensusWords({ count: null })).toBe('no census yet, and no enrolled count anywhere');
  });
});

describe('K20 K21 K25 what a click sends', () => {
  it('a route chip: nothing when already picked, null on the band route', () => {
    const request = { route: 'warner', route_default: 'direct' };
    expect(routeBody('warner', request)).toBeNull();
    expect(routeBody('direct', request)).toEqual({ route: null });
    expect(routeBody('warner', { route: 'direct', route_default: 'direct' })).toEqual({ route: 'warner' });
  });
  it('a chip sends only itself, added or removed', () => {
    expect(toggleBody('carriers', 'aetna', ['cigna'])).toEqual({ carriers: { add: ['aetna'] } });
    expect(toggleBody('funding', 'aso', ['aso'])).toEqual({ funding: { remove: ['aso'] } });
  });
  it('a chip tooltip says why it is dimmed, its note and its lines', () => {
    expect(chipTitle({ reason: 'Not on the 2–50 form', note: '51+ only.', line_labels: ['Medical'] })).toBe(
      'Not on the 2–50 form · 51+ only. · Medical',
    );
  });
});

describe('K.6 optimistic toggles', () => {
  it('two quick carrier clicks both show, in registry order', () => {
    const once = optimistic(page(), { carriers: { add: ['unum'] } }, FUNDING);
    const twice = optimistic(once, { carriers: { add: ['aetna'] } }, FUNDING);
    expect(twice.request.carriers).toEqual(['aetna', 'cigna', 'unum']);
    expect(twice.carriers.filter((c) => c.selected).map((c) => c.key)).toEqual(['aetna', 'cigna', 'unum']);
  });
  it('an emptied funding stays empty; a route back to the band follows it', () => {
    let shown = optimistic(page(), { funding: { remove: ['fully_insured'] } }, FUNDING);
    shown = optimistic(shown, { funding: { remove: ['level_funded'] } }, FUNDING);
    expect([shown.request.funding, shown.request.funding_default]).toEqual([[], false]);
    shown = optimistic(shown, { route: 'warner' }, FUNDING);
    expect([shown.request.route, shown.request.route_stored]).toEqual(['warner', 'warner']);
    shown = optimistic(shown, { route: null }, FUNDING);
    expect([shown.request.route, shown.request.route_stored]).toEqual(['direct', '']);
  });
  it('the answer replaces the request, the chips and the marks', () => {
    const answer = { request: { route: 'warner' }, carriers: [], done: {} };
    expect(adopt(page(), answer)).toMatchObject(answer);
  });
});

describe('K6 K7 K9 K10 the cards', () => {
  const cards = ['coverage', 'request', 'checklist', 'packet', 'emails'].map((key) => ({ key }));
  it('shows only the cards available, counts their marks', () => {
    const shown = shownCards(cards, { coverage: true, request: true, checklist: true });
    expect(shown).toEqual(['coverage', 'request', 'checklist']);
    expect(progress(shown, { request: {}, packet: {} })).toEqual({ done: 1, total: 3, all: false });
    expect(progress(['request'], { request: {} }).all).toBe(true);
  });
  it('a completed card comes back shut until this visit opens it', () => {
    expect(isOpen({}, { request: {} }, 'request')).toBe(false);
    expect(isOpen({}, {}, 'request')).toBe(true);
    expect(isOpen({ request: true }, { request: {} }, 'request')).toBe(true);
  });
  it('the checklist digest moves when a row or the meter moves, not otherwise', () => {
    const list = { tier: 'mid', required: 6, done: 1, items: [{ key: 'cobra', status: 'missing', done: false }] };
    const same = { ...list, items: [{ ...list.items[0], label: 'COBRA' }] };
    const ticked = { ...list, done: 2, items: [{ ...list.items[0], status: 'done', done: true }] };
    expect(checklistDigest(same)).toBe(checklistDigest(list));
    expect(checklistDigest(ticked)).not.toBe(checklistDigest(list));
    expect(checklistDigest(null)).toBeNull();
  });
});
