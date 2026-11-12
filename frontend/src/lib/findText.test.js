import { describe, expect, it } from 'vitest';
import { carrierForms, findFields, findHit, findMatches, findTerms, findWords, placeMatches } from './findText';

const CARRIERS = [
  { key: 'united_healthcare', name: 'UnitedHealthcare', aliases: ['UHC', 'United Healthcare', 'United'] },
  { key: 'united_concordia', name: 'United Concordia', aliases: [] },
  { key: 'florida_blue', name: 'Florida Blue', aliases: ['BCBS', 'Blue Cross Blue Shield of Florida'] },
  { key: 'aetna', name: 'Aetna', aliases: ['AFA'] },
];
const forms = carrierForms(CARRIERS);
const terms = (query) => findTerms(query, forms);
const place = (texts, carrier = null) => ({ fields: findFields(...texts), carrier });

describe('E61 the word rule', () => {
  it('needs every word, ignoring case and punctuation', () => {
    expect(findMatches(findFields('Choice Plus HDHP 3300'), findWords('choice HDHP'))).toBe(true);
    expect(findMatches(findFields('Choice Plus HDHP 3300'), findWords('choice gold'))).toBe(false);
    expect(findMatches(findFields('H1234-001'), findWords('h1234001'))).toBe(true);
    expect(findMatches(findFields('$1,500'), findWords('1500'))).toBe(true);
  });

  it('drops words with no letter or digit, and blanks never match', () => {
    expect(findWords(' - / ')).toEqual([]);
    expect(findFields('', null, '  ')).toEqual([]);
    expect(placeMatches(place([]), terms('aetna'))).toBe(false);
  });
});

describe('E64 carrier nicknames (OQ14)', () => {
  it('folds a run of words that names a carrier into one term', () => {
    expect(terms('UHC hdhp')).toEqual([{ word: 'uhc', carrier: 'united_healthcare' }, { word: 'hdhp' }]);
    expect(terms('blue cross blue shield of florida')).toEqual([
      { word: 'blue cross blue shield of florida', carrier: 'florida_blue' },
    ]);
  });

  it('"UHC" finds UnitedHealthcare by its carrier, never United Concordia', () => {
    const uhc = place(['Choice Plus 2000', 'UnitedHealthcare Consolidated'], 'united_healthcare');
    const concordia = place(['Dental PPO', 'United Concordia'], 'united_concordia');
    expect(placeMatches(uhc, terms('UHC'))).toBe(true);
    expect(placeMatches(concordia, terms('UHC'))).toBe(false);
  });
});

describe('E62 E63 the most specific hit', () => {
  const head = place(['Open Access HDHP 3300', 'Aetna'], 'aetna');
  const label = place(['Deductible (Single)']);
  const value = (text) => place([text, text]);

  it('a head or a label that answers alone is its own hit, not every value under it', () => {
    expect(placeMatches(head, terms('AFA'))).toBe(true);
    expect(findHit(terms('AFA'), value('$3,300'), label, head)).toBe(false);
    expect(findHit(terms('deductible'), value('$3,300'), label, head)).toBe(false);
  });

  it('a value answers alone, or with its row and column together', () => {
    expect(findHit(terms('3300'), value('$3,300'), label, head)).toBe(true);
    expect(findHit(terms('aetna deductible'), value('$3,300'), label, head)).toBe(true);
    expect(findHit(terms('aetna deductible'), value(''), label, head)).toBe(false);
    expect(findHit(terms('cigna deductible'), value('$3,300'), label, head)).toBe(false);
  });
});
