import { describe, expect, it } from 'vitest';
import { askableItems, hasNews, needWords, newWords, whoWords } from './threadModel';

const page = {
  intake: {
    sections: [{ key: 'company', fields: [{ key: 'fein', label: 'FEIN', shown: true }, { key: 'dba', label: 'DBA', shown: false }] }],
    blocks: { bor: { signed: false } },
  },
  people: [{ id: 4, title: 'Avery Synthetic', fields: [{ column: 'dob', label: 'Date of Birth' }] }],
  documents: [{ slot: 'claims', label: 'Claims experience report' }],
  census_file: { received: [] },
};

describe('L101 a client asks about what their page asks', () => {
  it('lists every item the page shows, by the server’s refs', () => {
    expect(askableItems(page)).toEqual([
      { ref: 'intake:fein', label: 'FEIN' },
      { ref: 'intake:block:bor', label: 'Broker of Record' },
      { ref: 'census:4:dob', label: 'Date of Birth — Avery Synthetic' },
      { ref: 'doc:claims', label: 'Claims experience report' },
      { ref: 'census:file', label: 'Your census file' },
    ]);
    expect(askableItems({})).toEqual([]);
  });
});

describe('L106 follow-up cards in the client’s words', () => {
  it('says what is new, who wrote, and how many need an answer', () => {
    expect(newWords({ new: true, replied: true })).toBe('New reply');
    expect(newWords({ new: true })).toBe('New note');
    expect(newWords({})).toBe('');
    expect(whoWords({ who: 'agency' }, 'Example')).toBe('Example');
    expect(whoWords({ who: 'you' }, 'Example')).toBe('You asked');
    expect(needWords([{ needs_answer: true }, { needs_answer: false }])).toBe('1 needs your answer');
    expect(hasNews([{ new: false }, { replied: true }])).toBe(true);
  });
});
