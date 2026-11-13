import { describe, expect, it } from 'vitest';
import { cellOf, focusOf, keepDecided, pickedSection, readyWords, sectionsOf, summaryOf } from './queueWords';

const meta = { queue_sections: [{ key: 'census', label: 'Census · client' }, { key: 'intake', label: 'Intake' }] };

describe('L11 the queue opens on a section', () => {
  const board = { sections: { census: { to_review: 0, questions: 0 }, intake: { to_review: 2, questions: 1 } } };
  const sections = sectionsOf(meta, board);

  it('counts each section’s answers and questions, in the old order', () => {
    expect(sections).toEqual([
      { key: 'census', label: 'Census · client', count: 0, questions: 0 },
      { key: 'intake', label: 'Intake', count: 3, questions: 1 },
    ]);
  });

  it('follows ?section=, else the first with something in it', () => {
    expect(pickedSection(sections, 'census').key).toBe('census');
    expect(pickedSection(sections, null).key).toBe('intake');
    expect(pickedSection([], null)).toBe(null);
  });
});

describe('L16 a row says what came back', () => {
  it('old → new, a blank says blank, and a carrier’s column is flagged', () => {
    const item = { kind: 'answer', person: 'Avery One', label: 'ZIP', ours: '', theirs: '33606', blocks: ['Aetna'] };
    expect(summaryOf(item)).toEqual({ title: 'Avery One · ZIP', sub: 'blank → 33606', flag: 'blocks Aetna' });
  });

  it('a block lists its lines; a new person is named', () => {
    expect(summaryOf({ kind: 'block', label: 'Lines to quote', ours: [], theirs: ['Dental', 'Vision'] }).sub).toBe(
      'blank → Dental; Vision',
    );
    expect(summaryOf({ kind: 'person', person: 'Rowan S', theirs: 'Rowan S' }).sub).toBe('New person · Rowan S');
  });

  it('why an answer is ready', () => {
    expect(readyWords({ ready_why: 'submitted' })).toBe('Submitted');
    expect(readyWords({ ready_why: 'idle', idle_days: 2 })).toBe('Not submitted · idle 2 days');
    expect(readyWords({ ready_why: '' })).toBe('Still typing');
  });

  it('a ref names what a correction writes', () => {
    expect(cellOf('census:12:zip')).toEqual({ surface: 'census', memberId: 12, column: 'zip' });
    expect(cellOf('intake:block:lines')).toEqual({ surface: 'intake', key: 'block:lines' });
    expect(cellOf('q:fl_blue_51:plans.3.txtCurrPlanName')).toEqual({
      surface: 'questionnaire',
      form: 'fl_blue_51',
      slot: 'plans.3.txtCurrPlanName',
    });
  });
});

describe('L15 decided rows stay for the visit', () => {
  const a = { id: 'a', phase: 'to_review', group: 'zip:changed' };
  const b = { id: 'b', phase: 'to_review', group: 'zip:changed' };
  const c = { id: 'c', phase: 'to_review', group: 'dob:filled' };

  it('puts a decided row back where it stood after a read drops it', () => {
    const decided = { b: { label: 'Approved', item: b, index: 1 } };
    expect(keepDecided([a, c], decided, { phase: 'to_review' })).toEqual([a, b, c]);
    expect(keepDecided([a, c], {}, { phase: 'to_review' })).toEqual([a, c]);
  });

  it('only in the phase and group it belongs to', () => {
    const decided = { b: { item: b, index: 1 } };
    expect(keepDecided([c], decided, { phase: 'to_review', group: 'dob:filled' })).toEqual([c]);
    expect(keepDecided([], decided, { phase: 'in_progress' })).toEqual([]);
  });

  it('opens the row asked for, else the first one open', () => {
    expect(focusOf([a, b], 'b', {})).toBe('b');
    expect(focusOf([a, b], 'x', { a: {} })).toBe('b');
    expect(focusOf([], 'x', {})).toBe(null);
  });
});
