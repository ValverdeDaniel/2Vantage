import { describe, expect, it } from 'vitest';
import { asksOf, bodyOf, createWords, dayIn, floorKey, hasAsk, initialState, linkCount, toggled, typedPerson } from './newLinkModel';

const state = (part) => ({ ...initialState(), ...part });

describe('the minimal New link (L40)', () => {
  it('asks only the parts picked, in the stored shape', () => {
    expect(asksOf(state({}))).toEqual({});
    expect(hasAsk(state({}))).toBe(false);
    expect(asksOf(state({ intake: 'required', censusFile: true, documents: true }))).toEqual({
      intake: { scope: 'required' },
      census: { scope: 'none', file: true },
      documents: { missing: true },
    });
    expect(asksOf(state({ census: 'missing' }))).toEqual({ census: { scope: 'missing', file: false } });
  });

  it('sends contacts by id and typed people by name, the date only when picked', () => {
    const body = bodyOf(state({ contactIds: [4], typed: [{ name: 'Sam', email: '' }], intake: 'all', message: ' Hi ' }));
    expect(body).toEqual({
      people: [{ contact_id: 4 }, { name: 'Sam', email: '' }],
      asks: { intake: { scope: 'all' } },
      message: 'Hi',
      security: 'link',
      blank: false,
    });
    expect(bodyOf(state({ intake: 'all', expiresOn: '2026-11-20' })).expires_on).toBe('2026-11-20');
  });

  it('makes one link per person, or one private link', () => {
    expect(linkCount(state({}))).toBe(1);
    expect(createWords(state({}), false)).toBe('Create link');
    expect(createWords(state({ contactIds: [1, 2], typed: [{ name: 'A' }] }), false)).toBe('Create 3 links');
    expect(createWords(state({}), true)).toBe('Creating…');
  });

  it('keys the floor on what is asked, never on who', () => {
    expect(floorKey(state({ census: 'missing', contactIds: [1] }))).toBe(floorKey(state({ census: 'missing' })));
  });

  it('needs a name for a typed person and keeps the order picked', () => {
    expect(typedPerson('  Pat   Example ', ' pat@example.com ')).toEqual({ name: 'Pat Example', email: 'pat@example.com' });
    expect(typedPerson(' ', 'x@example.com')).toBeNull();
    expect(toggled([1, 2], 3)).toEqual([1, 2, 3]);
    expect(toggled([1, 2, 3], 2)).toEqual([1, 3]);
  });

  it('names local days', () => {
    expect(dayIn(7, new Date(2026, 10, 28))).toBe('2026-12-05');
  });
});

describe('the builder asks questionnaires (slice 58)', () => {
  it('G80 asks each form online or as a signed copy, and leaves an unpicked form off', () => {
    const picked = { ...initialState(), forms: { fl_blue_51: 'online', stop_loss_siia: 'upload', wp_lg: '' } };
    expect(asksOf(picked).questionnaires).toEqual([
      { form: 'fl_blue_51', mode: 'online', picks: { fields: [], blocks: [] } },
      { form: 'stop_loss_siia', mode: 'upload', picks: { fields: [], blocks: [] } },
    ]);
    expect(hasAsk({ ...initialState(), forms: { fl_blue_51: 'online' } })).toBe(true);
  });
});
