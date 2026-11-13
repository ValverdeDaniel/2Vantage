import { describe, expect, it } from 'vitest';
import { marginRefs, placeCards } from './placeCards';

describe('the comment margin (L31)', () => {
  it('L31 each card sits at its item, or under the card above it', () => {
    expect(placeCards([0, 10, 200], [50, 50, 50], -1, 10)).toEqual([0, 60, 200]);
  });

  it('L31 the picked card lines up with its item and the others make room', () => {
    expect(placeCards([0, 100, 120], [50, 50, 50], 2, 10)).toEqual([0, 60, 120]);
  });

  it('L31 with no room above the picked card, everything goes from the top', () => {
    expect(placeCards([0, 20], [50, 50], 1, 10)).toEqual([0, 60]);
  });

  it('L31 holds a card only where there is a conversation, an answer, a question or the pick', () => {
    const items = [
      { ref: 'a', status: 'missing' },
      { ref: 'b', status: 'answered' },
      { ref: 'c', status: 'question' },
      { ref: 'd', status: 'on_file' },
      { ref: 'e', status: 'missing' },
    ];
    expect(marginRefs(items, { d: [{ id: 1 }] }, 'e')).toEqual(['b', 'c', 'd', 'e']);
  });
});
