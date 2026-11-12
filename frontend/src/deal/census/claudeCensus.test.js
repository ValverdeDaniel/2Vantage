import { describe, expect, it } from 'vitest';
import { censusReader, readBanner, readSubtitle } from './claudeCensus';

describe('Claude on the Census tab (D41, C9, slice 51)', () => {
  it('D41 offers the door only with the census reader, greyed with the reason while the PHI gate keeps it off', () => {
    expect(censusReader({}).state).toBe('');
    expect(censusReader({ ai: { targets: [{ key: 'census', kinds: ['census'] }], phi_readers: true } }).state).toBe(
      'on',
    );
    const off = censusReader({ ai: { targets: [{ key: 'quotes', kinds: ['quote'] }], phi_readers: false, phi_off: 'Why.' } });
    expect(off).toEqual({ state: 'off', why: 'Why.' });
  });

  it('C9 says a read census waits, not applied', () => {
    expect(readBanner({ document_name: 'roster.pdf' })).toBe(
      '“roster.pdf” came in through Work with Claude and was read, not applied — nothing on the roster has changed.',
    );
    expect(readSubtitle({ document_name: 'roster.pdf', people: 4 }, 9, 10)).toBe(
      'roster.pdf · read by Claude · 4 people · 9 of 10 columns mapped',
    );
  });
});
