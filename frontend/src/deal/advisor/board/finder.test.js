import { describe, expect, it } from 'vitest';
import { findMatches, findFields, findWords } from '../../../lib/findText';
import { carrierForms, emptyNote, findTerms, otherHits, prepareIndex, runFinder } from './finder';

// As /api/meta/ serves them (deals/carriers.py); synthetic plans.
const CARRIERS = [
  { key: 'unitedhealthcare', name: 'UnitedHealthcare', aliases: ['UHC', 'United Healthcare', 'United'] },
  { key: 'united_concordia', name: 'United Concordia', aliases: [] },
  { key: 'florida_blue', name: 'Florida Blue', aliases: ['FL Blue', 'BCBS', 'Blue Cross Blue Shield of Florida'] },
  { key: 'cigna', name: 'Cigna', aliases: [] },
];
const forms = carrierForms(CARRIERS);

const INDEX = prepareIndex([
  { id: 1, line: 'medical', current: true, carrier: 'unitedhealthcare', texts: ['Choice Plus 1000', 'UnitedHealthcare'] },
  { id: 2, line: 'medical', current: false, carrier: 'unitedhealthcare', texts: ['Choice Plus HDHP 3300', 'UnitedHealthcare', 'HDHP'] },
  { id: 3, line: 'medical', current: false, carrier: 'unitedhealthcare', texts: ['Choice Plus 2000', 'UnitedHealthcare Consolidated', 'H1234-001'] },
  { id: 4, line: 'medical', current: false, carrier: 'cigna', texts: ['LocalPlus HDHP 3000', 'Cigna', 'HDHP'] },
  { id: 5, line: 'dental', current: false, carrier: 'unitedhealthcare', texts: ['Dental PPO 1500', 'UHC'] },
  { id: 6, line: 'dental', current: false, carrier: 'united_concordia', texts: ['Dental Plus', 'United Concordia'] },
  { id: 7, line: 'medical', current: false, carrier: 'florida_blue', texts: ['BlueOptions 5000', 'BCBS of Florida'] },
  { id: 8, line: 'vision', current: false, carrier: null, texts: ['Choice 10/25', 'VSP'] },
]);

const ids = (finder) => [...finder.ids].sort((a, b) => a - b);

describe('the word rule (findText, E61)', () => {
  it('every word must match, as typed or as its letters and digits; punctuation words are dropped', () => {
    const fields = findFields('Choice Plus 2000', 'H1234-001', '$1,500');
    expect(findMatches(fields, findWords('choice h1234001'))).toBe(true);
    expect(findMatches(fields, findWords('1500'))).toBe(true);
    expect(findMatches(fields, findWords('choice gold'))).toBe(false);
    expect(findWords(' - / ')).toEqual([]);
  });
});

describe('finder (F14, OQ14)', () => {
  it('"UHC" finds every UnitedHealthcare quote on every line, and no United Concordia plan', () => {
    const finder = runFinder(INDEX, 'UHC', forms);
    expect(ids(finder)).toEqual([2, 3, 5]);
    expect(finder.byLine.get('medical')).toEqual([2, 3]);
    expect(finder.byLine.get('dental')).toEqual([5]);
  });

  it('the carrier name finds a plan typed with its alias, and the other way round', () => {
    expect(ids(runFinder(INDEX, 'unitedhealthcare dental', forms))).toEqual([5]);
    expect(ids(runFinder(INDEX, 'Florida Blue', forms))).toEqual([7]);
    expect(ids(runFinder(INDEX, 'blue cross blue shield of florida', forms))).toEqual([7]);
  });

  it('aliases come from meta: without them "UHC" finds only the plan whose text says UHC', () => {
    expect(ids(runFinder(INDEX, 'UHC', carrierForms([])))).toEqual([5]);
  });

  it('every word must match: a carrier with a plan word narrows', () => {
    expect(ids(runFinder(INDEX, 'uhc hdhp', forms))).toEqual([2]);
    expect(ids(runFinder(INDEX, 'hdhp', forms))).toEqual([2, 4]);
  });

  it('plan numbers match by their letters and digits', () => {
    expect(ids(runFinder(INDEX, 'h1234001', forms))).toEqual([3]);
  });

  it('current plans never count as hits', () => {
    expect(ids(runFinder(INDEX, 'Choice Plus 1000', forms))).toEqual([]);
  });

  it('nothing typed is an inactive finder', () => {
    const finder = runFinder(INDEX, '  ', forms);
    expect(finder.active).toBe(false);
    expect(finder.ids.size).toBe(0);
  });

  it('a run of words naming a carrier is one term', () => {
    expect(findTerms('fl blue ppo', forms)).toEqual([{ word: 'fl blue', carrier: 'florida_blue' }, { word: 'ppo' }]);
  });
});

describe('other lines and the empty board (F15, F17)', () => {
  const lines = [
    { line: 'medical', label: 'Medical' },
    { line: 'dental', label: 'Dental' },
    { line: 'vision', label: 'Vision' },
  ];

  it('"Also matches N on Dental" lists the other lines with hits, in the deal\'s order', () => {
    const finder = runFinder(INDEX, 'UHC', forms);
    expect(otherHits(finder, 'medical', lines)).toEqual([{ line: 'dental', label: 'Dental', count: 1 }]);
    expect(otherHits(finder, 'vision', lines).map((hit) => hit.line)).toEqual(['medical', 'dental']);
    expect(otherHits(runFinder(INDEX, '', forms), 'medical', lines)).toEqual([]);
  });

  it('the empty board says why', () => {
    const finder = runFinder(INDEX, 'UHC', forms);
    const others = otherHits(finder, 'vision', lines);
    expect(emptyNote({ finder, line: 'vision', lineLabel: 'Vision', others, quoteCount: 1 })).toBe(
      'Nothing on Vision matches “UHC”, but 2 plans on Medical and 1 plan on Dental do. Pick a line under the search box.',
    );
    expect(emptyNote({ finder, line: 'dental', lineLabel: 'Dental', others: [], quoteCount: 2 })).toBe(
      '1 plan on Dental matches “UHC”, but the other filters hide it. Clear resets them.',
    );
    expect(emptyNote({ finder: runFinder(INDEX, '', forms), line: 'medical', lineLabel: 'Medical', quoteCount: 4 })).toBe(
      'No plans match the current filters.',
    );
    expect(emptyNote({ finder, line: 'medical', lineLabel: 'Medical', quoteCount: 0 })).toBe(
      'No quoted plans on Medical yet — only the current plans.',
    );
  });
});
