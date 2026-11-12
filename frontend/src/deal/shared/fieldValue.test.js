import { describe, expect, it } from 'vitest';
import { affixes, draftOf, isBlank, multiParts, sameAnswer, shownValue, toggleOption } from './fieldValue';

const STATES = ['FL', 'GA', 'TX'];

describe('a typed answer as text (B3)', () => {
  it('shows a list with commas and anything else as stored', () => {
    expect(shownValue(['FL', 'GA'])).toBe('FL, GA');
    expect(shownValue('62000')).toBe('62000');
    expect(shownValue(null)).toBe('');
    expect(draftOf(['FL'])).toBe('FL');
    expect(isBlank([])).toBe(true);
    expect(isBlank('0')).toBe(false);
  });

  it('reads the options a multi names, the way the server splits them', () => {
    expect(multiParts('fl; ga/ fl, Atlantis', STATES)).toEqual({ picked: ['FL', 'GA'], unknown: ['Atlantis'] });
    expect(multiParts('', STATES)).toEqual({ picked: [], unknown: [] });
  });

  it('switches a chip in the text and keeps the unknown parts for the server to refuse', () => {
    expect(toggleOption('FL', 'GA', STATES)).toBe('FL, GA');
    expect(toggleOption('fl, GA', 'FL', STATES)).toBe('GA');
    expect(toggleOption('FL, Atlantis', 'TX', STATES)).toBe('FL, TX, Atlantis');
  });

  it('writes nothing when the editor holds the stored answer', () => {
    expect(sameAnswer(' FL, GA ', ['FL', 'GA'])).toBe(true);
    expect(sameAnswer('GA', ['FL', 'GA'])).toBe(false);
    expect(sameAnswer('', null)).toBe(true);
  });

  it('puts $ before money and % after a percent', () => {
    expect(affixes('money')).toEqual({ before: '$', after: '' });
    expect(affixes('percent')).toEqual({ before: '', after: '%' });
    expect(affixes('number')).toEqual({ before: '', after: '' });
  });
});
