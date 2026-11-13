import { describe, expect, it } from 'vitest';
import { fixUrl, nextFor, returnedOf, returnText, sectionNumbers, taking, whoOf } from './sectionModel';

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
  it('L16 waiting also holds the answers sent back and not answered since (slice 56)', () => {
    expect(sectionNumbers({ ...section, going_back: 2, in_tray: 1 })).toEqual({ review: 4, waiting: 3, missing: 4, inTray: 1 });
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

describe('the section bar Next line (L14)', () => {
  it('L14 keeps the section’s own first entry, or a link running out', () => {
    const entries = [
      { kind: 'blocks', surface: 'census', label: 'c' },
      { kind: 'link_expiring', surface: '', label: 'l' },
      { kind: 'blocks', surface: 'intake', label: 'i' },
    ];
    expect(nextFor(entries, 'intake').label).toBe('l');
    expect(nextFor(entries, 'census').label).toBe('c');
    expect(nextFor([], 'intake')).toBeNull();
  });

  it('L14 a fix lands on the Review tab view or its own tab', () => {
    expect(fixUrl(7, { tab: 'review', view: 'board', section: 'census' })).toBe('/deals/7/review?section=census');
    expect(fixUrl(7, { tab: 'review', view: 'request', pane: 'census' })).toBe('/deals/7/review?view=request&pane=census');
    expect(fixUrl(7, { tab: 'documents' })).toBe('/deals/7/documents');
  });

  it('L135 a staged client read opens its census import, or Work with Claude on the Intake tab', () => {
    expect(fixUrl(7, { tab: 'census', params: { import: 41 } })).toBe('/deals/7/census?import=41');
    expect(fixUrl(7, { tab: 'intake', params: { claude: '1' } })).toBe('/deals/7/intake?claude=1');
    expect(fixUrl(7, { tab: 'census', params: { import: null } })).toBe('/deals/7/census');
  });
});
