import { describe, expect, it } from 'vitest';
import {
  answersReducer,
  cellRef,
  expiryWords,
  fieldShown,
  groupFields,
  initialAnswers,
  intakeRef,
  liveRail,
  nothingAsked,
  pendingAnswers,
  ruleMet,
  sentValues,
  todoStatus,
} from './portalModel';

const PAGE = {
  intake: {
    sections: [
      {
        key: 'employer',
        fields: [
          { key: 'fein', value: '', base: 'b1', shown: true, shown_when: null, locked: false },
          { key: 'states', value: ['FL', 'GA'], base: 'b2', shown: true, shown_when: null, locked: false },
          { key: 'locations', value: '', base: 'b3', shown: false, shown_when: { field: 'multi', op: 'eq', value: 'Yes' } },
          { key: 'legal_name', value: 'Acme', base: 'b4', shown: true, shown_when: null, locked: true },
        ],
      },
    ],
    blocks: { lines: { value: ['medical'], base: 'b5' } },
  },
  people: [{ id: 7, fields: [{ column: 'dob', value: '', base: 'c1', group: 'demographics', group_label: 'Personal details' }] }],
  checklist: {
    items: [
      { key: 'intake', kind: 'fields', filled: 2, total: 3, done: false },
      { key: 'people', kind: 'fields', filled: 0, total: 1, done: false },
      { key: 'census', kind: 'census_upload', done: false },
      { key: 'doc_invoice', kind: 'document', done: false },
    ],
  },
};

describe('the answers (L95, L96)', () => {
  it('seeds every ref with the value shown and its base, a multi as typed text', () => {
    const state = initialAnswers(PAGE);
    expect(state.values[intakeRef('states')]).toBe('FL, GA');
    expect(state.values['intake:block:lines']).toEqual(['medical']);
    expect(state.bases[cellRef(7, 'dob')]).toBe('c1');
    expect(pendingAnswers(state)).toEqual({});
  });

  it('sends only what changed since it was taken, with its base', () => {
    let state = initialAnswers(PAGE);
    state = answersReducer(state, { type: 'set', ref: intakeRef('fein'), value: '12-3456789' });
    const pending = pendingAnswers(state);
    expect(pending).toEqual({ 'intake:fein': { value: '12-3456789', base: 'b1' } });
    state = answersReducer(state, { type: 'saved', sent: sentValues(pending), bases: { 'intake:fein': 'b9' } });
    expect(pendingAnswers(state)).toEqual({});
    expect(state.bases['intake:fein']).toBe('b9');
  });

  it('holds a conflict until they keep theirs or use theirs base for mine', () => {
    let state = answersReducer(initialAnswers(PAGE), { type: 'set', ref: 'intake:fein', value: '11-1111111' });
    state = answersReducer(state, { type: 'conflicts', list: [{ ref: 'intake:fein', theirs: '22-2222222', base: 'b7' }] });
    expect(pendingAnswers(state)).toEqual({});
    const mine = answersReducer(state, { type: 'useMine', ref: 'intake:fein' });
    expect(pendingAnswers(mine)).toEqual({ 'intake:fein': { value: '11-1111111', base: 'b7' } });
    const theirs = answersReducer(state, { type: 'keepTheirs', ref: 'intake:fein' });
    expect(theirs.values['intake:fein']).toBe('22-2222222');
    expect(pendingAnswers(theirs)).toEqual({});
  });

  it('waits on a refused answer until it is changed', () => {
    let state = answersReducer(initialAnswers(PAGE), { type: 'set', ref: 'intake:fein', value: 'nope' });
    state = answersReducer(state, { type: 'refused', errors: { 'intake:fein': 'FEIN takes XX-XXXXXXX' } });
    expect(pendingAnswers(state)).toEqual({});
    state = answersReducer(state, { type: 'set', ref: 'intake:fein', value: '12-3456789' });
    expect(Object.keys(pendingAnswers(state))).toEqual(['intake:fein']);
  });

  it('a fresh page keeps what was typed and not yet taken', () => {
    let state = answersReducer(initialAnswers(PAGE), { type: 'set', ref: 'intake:fein', value: '12' });
    state = answersReducer(state, { type: 'reseed', page: PAGE });
    expect(state.values['intake:fein']).toBe('12');
  });
});

describe('what shows and what is left (L81, L83)', () => {
  it('reads a rule as the old conditionMet did', () => {
    expect(ruleMet({ field: 'x', op: 'eq', value: 'Yes' }, 'Yes')).toBe(true);
    expect(ruleMet({ field: 'x', op: 'gt', value: '50' }, '$1,200')).toBe(true);
    expect(ruleMet({ field: 'x', op: 'gte', value: '50' }, 'many')).toBe(false);
    expect(ruleMet({ field: 'x' }, '')).toBe(false);
  });

  it('re-reads a rule as they type when the page asks its question', () => {
    const field = PAGE.intake.sections[0].fields[2];
    expect(fieldShown(field, { 'intake:multi': 'No' })).toBe(false);
    expect(fieldShown(field, { 'intake:multi': 'Yes' })).toBe(true);
  });

  it('recounts the to-do list from what is on screen and the files staged', () => {
    let state = initialAnswers(PAGE);
    state = answersReducer(state, { type: 'set', ref: 'intake:fein', value: '12-3456789' });
    const rail = liveRail(PAGE, state.values, { invoice: [{ name: 'a.pdf' }] });
    const byKey = Object.fromEntries(rail.items.map((item) => [item.key, item]));
    expect([byKey.intake.filled, byKey.intake.total, byKey.intake.done]).toEqual([3, 3, true]);
    expect(todoStatus(byKey.doc_invoice)).toBe('attached — save to send');
    expect(todoStatus(byKey.census)).toBe('needed');
    expect([rail.done, rail.total]).toEqual([2, 4]);
  });

  it('says how long the link lasts, and when nothing is asked', () => {
    expect(expiryWords(1)).toBe('Secure link · expires in 1 day');
    expect(expiryWords(6)).toBe('Secure link · expires in 6 days');
    expect(nothingAsked({ intake: null, people: [], census_file: null, documents: [], add_people: null })).toBe(true);
    expect(nothingAsked(PAGE)).toBe(false);
  });

  it('groups a person’s fields under the employer’s headings', () => {
    expect(groupFields(PAGE.people[0].fields)).toEqual([
      { key: 'demographics', label: 'Personal details', fields: PAGE.people[0].fields },
    ]);
  });
});
