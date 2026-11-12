import { describe, expect, it } from 'vitest';
import { returnedOf, returnText, sectionNumbers, taking, whoOf } from './sectionModel';

const section = {
  to_review: 3,
  in_progress: 1,
  ready: 2,
  ready_submitted: 1,
  ready_idle: 1,
  names: ['Dana', 'Lee'],
  questions: 1,
  missing: 4,
  in_tray: 0,
};

describe('L14 the section bar counts', () => {
  it('to review holds the questions; waiting is what is still typed', () => {
    expect(sectionNumbers(section)).toEqual({ review: 4, waiting: 1, missing: 4, inTray: 0 });
    expect(sectionNumbers(undefined)).toEqual({ review: 0, waiting: 0, missing: 0, inTray: 0 });
  });

  it('says who answered and what is ready', () => {
    const returned = returnedOf(section);
    expect(returnText(returned)).toBe('↩ Dana and Lee answered 4 · 2 ready · 1 still typing · 1 to look at · 1 question');
    expect(returnText(returnedOf({ questions: 2 }))).toBe('↩ The client asked 2 questions');
    expect(whoOf(['A', 'B', 'C', 'D'])).toBe('A, B and 2 more');
  });

  it('C34 Approve N ready takes the submitted answers, an idle link’s only with the tick', () => {
    const returned = returnedOf(section);
    expect(taking(returned, false)).toBe(1);
    expect(taking(returned, true)).toBe(2);
  });
});
