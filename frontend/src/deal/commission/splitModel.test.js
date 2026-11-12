import { describe, expect, it } from 'vitest';
import {
  addRow,
  changeRole,
  complete,
  draftFrom,
  person,
  pickPerson,
  rowError,
  rowsFor,
  saveLabel,
  shareFor,
  topError,
  usedKeys,
} from './splitModel';

const PCT = (value) => ({ type: 'pct', value });
const split = {
  source: 'deal',
  rows: [
    { key: 'u5', role: 'primary', amount: null, basis: 'pool' },
    { key: 'p2', role: 'referral', amount: PCT('10'), renewal_amount: PCT('0'), basis: 'gross', works_it: false },
  ],
};
const people = [
  { key: 'u5', kind: 'producer' },
  { key: 'p2', kind: 'partner', default_split: PCT('15') },
  { key: 'p3', kind: 'producer', default_split: PCT('40') },
];

describe('the split draft (H12, H18–H20)', () => {
  it('H12 reads the payload and sends the primary first with every term', () => {
    const draft = draftFrom(split);
    expect(draft.primary).toBe('u5');
    expect(draft.rows[0].terms_open).toBe(true);
    expect(rowsFor(draft)).toEqual([
      { user: 5, role: 'primary' },
      {
        party: 2,
        role: 'referral',
        amount: PCT('10'),
        renewal_amount: PCT('0'),
        expires_after_years: null,
        basis: 'gross',
        works_it: false,
      },
    ]);
  });

  it('H12 a pick fills an empty amount from the default split; a role keeps only its kinds', () => {
    let draft = addRow(draftFrom(split), 'secondary');
    expect(complete(draft)).toBe(false);
    draft = pickPerson(draft, 1, 'p3', people);
    expect(draft.rows[1]).toMatchObject({ key: 'p3', amount: PCT('40'), works_it: true });
    expect(complete(draft)).toBe(true);
    const kinds = { secondary: ['producer'], split: ['producer', 'partner'], referral: ['partner'] };
    expect(changeRole(draft, 1, 'split', people, kinds).rows[1].key).toBe('p3');
    expect(changeRole(draft, 1, 'referral', people, kinds).rows[1].key).toBe(null);
    expect(usedKeys(draft, 1)).toEqual(['u5', 'p2']);
  });

  it('H18 errors are found by the row index the server used', () => {
    const draft = draftFrom(split);
    const errors = { 'rows.1.amount': ['Enter the split amount'], 'rows.split_total': ['Too much'] };
    expect(rowError(errors, draft, 0)).toBe('Enter the split amount');
    expect(topError(errors, draft, 'split_total')).toBe('Too much');
    expect(topError({ 'rows.0.party': ['The primary producer must be appointed'] }, draft, 'primary')).toBe(
      'The primary producer must be appointed',
    );
    expect(rowError(errors, { ...draft, primary: null }, 0)).toBe('');
  });

  it('H18 shares are matched by person and role', () => {
    const preview = { shares: [{ key: null, role: 'house' }, { key: 'u5', role: 'primary', pct: '24' }] };
    expect(shareFor(preview, 'u5', 'primary').pct).toBe('24');
    expect(shareFor(preview, 'p9', 'split')).toBe(null);
  });

  it('H20 names a person key the way the API does, and says what Save will do', () => {
    expect(person('p12')).toEqual({ party: 12 });
    expect(person('u3')).toEqual({ user: 3 });
    expect(person('x')).toEqual({});
    expect(saveLabel({ scope: 'client', source: 'deal' })).toBe('Save for this client');
    expect(saveLabel({ scope: 'deal', source: 'deal' })).toBe('Save changes');
    expect(saveLabel({ scope: 'deal', source: 'client' })).toBe('Save for this deal');
    expect(saveLabel({ clientOnly: true })).toBe('Save for this client');
    expect(saveLabel({ saving: true })).toBe('Saving…');
  });
});
