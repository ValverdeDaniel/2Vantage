import { describe, expect, it } from 'vitest';
import { canRead, readWords } from './fileRows';

describe("the client's files in the To review lane (L125; slice 59)", () => {
  it('offers Read with Claude only for a file a reader reads and nobody has read', () => {
    expect(canRead({ reader: 'quotes', read: '' })).toBe(true);
    expect(canRead({ reader: '', read: '' })).toBe(false);
    expect(canRead({ reader: 'census', read: 'waiting' })).toBe(false);
    expect(canRead({ reader: 'intake', read: 'reading' })).toBe(false);
    expect(canRead({ reader: 'census', read: 'used' })).toBe(false);
  });

  it('says where a read stands', () => {
    expect(readWords({ read: 'reading' })).toBe('Being read');
    expect(readWords({ read: 'waiting' })).toBe('Read — waiting for review');
    expect(readWords({ read: '' })).toBe('');
  });
});
