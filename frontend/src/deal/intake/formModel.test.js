import { describe, expect, it } from 'vitest';
import {
  buildSections,
  missingKeys,
  missingLabels,
  nextRow,
  revealsOthers,
  selectable,
  withAnswer,
  withReply,
} from './formModel';
import { viewOf } from './views';

const q = (key, extra = {}) => ({ key, label: key.toUpperCase(), type: 'text', need: '', ...extra });
const FORM = {
  sections: [
    { key: 'a', label: 'A', questions: [q('one', { need: 'Q' }), q('two'), q('reveal', { type: 'yesno' })] },
    {
      key: 'b',
      label: 'B',
      questions: [q('three', { need: 'Q' }), q('hidden', { shown_when: { field: 'reveal', op: 'eq', value: 'Yes' } })],
    },
    { key: 'goals', label: 'Goals', questions: [q('four')] },
  ],
  guidance: { key: 'client_guidance', section: 'goals', label: 'Client guidance', type: 'text', limit: 4000 },
};
const DATA = {
  answers: { two: 'x', four: 'y' },
  sources: { two: { origin: 'typed' } },
  hidden: ['hidden'],
  needed: ['one', 'three'],
  status: { one: 'missing', three: 'missing' },
  issues: { two: [{ code: 'c', severity: 'warning', message: 'm' }] },
};

const keys = (sections) => sections.flatMap((s) => s.rows.map((r) => r.key));

describe('the four cards (B1, B2)', () => {
  it('builds the rows with their state, the guidance last on Goals', () => {
    const sections = buildSections(FORM, DATA);
    expect(keys(sections)).toEqual(['one', 'two', 'reveal', 'three', 'hidden', 'four', 'client_guidance']);
    const [one, two] = sections[0].rows;
    expect(one).toMatchObject({ value: '', needed: true, status: 'missing', visible: true });
    expect(two).toMatchObject({ value: 'x', needed: false, issues: DATA.issues.two, source: { origin: 'typed' } });
    expect(sections[1].rows[1].visible).toBe(false);
    expect(sections[2].rows[1]).toMatchObject({ guidance: true, needed: false });
  });

  it('reads nothing as an empty form', () => {
    expect(buildSections(undefined, DATA)).toEqual([]);
    expect(buildSections(FORM, undefined)[0].rows[0]).toMatchObject({ value: '', visible: true, needed: false });
  });
});

describe('the Enter / Tab flow (B5)', () => {
  const sections = buildSections(FORM, DATA);
  it('Enter goes to the very next shown question, filled or not, across cards, skipping hidden ones', () => {
    expect(nextRow(sections, 'one').key).toBe('two');
    expect(nextRow(sections, 'three').key).toBe('four');
    expect(nextRow(sections, 'client_guidance').key).toBe('one');
  });

  it('Tab goes to the next blank question this deal needs; Shift goes back', () => {
    expect(nextRow(sections, 'one', { required: true }).key).toBe('three');
    expect(nextRow(sections, 'three', { required: true }).key).toBe('one');
    expect(nextRow(sections, 'four', { back: true }).key).toBe('three');
    expect(nextRow(sections, null).key).toBe('one');
  });

  it('names nothing when nothing is left', () => {
    const done = buildSections(FORM, { ...DATA, answers: { one: 'a', three: 'b' } });
    expect(nextRow(done, 'one', { required: true })).toBeNull();
  });

  it('knows which answers reveal others', () => {
    expect(revealsOthers(FORM, 'reveal')).toBe(true);
    expect(revealsOthers(FORM, 'two')).toBe(false);
  });
});

describe('the copy on screen (B4)', () => {
  it('shows a typed answer at once and clears a blank one', () => {
    expect(withAnswer(DATA, 'one', 'Example').answers.one).toBe('Example');
    expect('two' in withAnswer(DATA, 'two', '').answers).toBe(false);
    expect(withAnswer(undefined, 'one', 'x')).toBeUndefined();
  });

  it('lays the reply over it: changed answers and sources, then the form state', () => {
    const reply = {
      answers: { two: null, one: 'Example' },
      sources: { two: null, one: { origin: 'typed' } },
      hidden: [],
      needed: ['one', 'three', 'hidden'],
      status: { three: 'missing', hidden: 'missing' },
      issues: {},
    };
    const next = withReply(DATA, reply);
    expect(next.answers).toEqual({ one: 'Example', four: 'y' });
    expect(next.sources).toEqual({ one: { origin: 'typed' } });
    expect(next.hidden).toEqual([]);
    expect(missingLabels(buildSections(FORM, next))).toEqual(['THREE', 'HIDDEN']);
  });
});

describe('☑ Select fields (B10)', () => {
  it('ticks blanks, open warnings and marked answers, never a settled one', () => {
    expect(selectable({ value: '', status: 'missing' })).toBe(true);
    expect(selectable({ value: 'x', status: 'to_check' })).toBe(true);
    expect(selectable({ value: 'x', source: { origin: 'typed', mark: { state: 'ignored' } } })).toBe(true);
    expect(selectable({ value: 'x', source: { origin: 'typed' } })).toBe(false);
  });

  it('"Select all missing" picks the needed blanks only, not every blank', () => {
    expect(missingKeys(buildSections(FORM, DATA))).toEqual(['one', 'three']);
  });
});

describe('the views (B36)', () => {
  it('opens the Form unless the URL names a built view', () => {
    expect(viewOf(new URLSearchParams(''))).toBe('form');
    expect(viewOf(new URLSearchParams('view=board'))).toBe('form');
    expect(viewOf(new URLSearchParams('view=form'))).toBe('form');
  });
});
