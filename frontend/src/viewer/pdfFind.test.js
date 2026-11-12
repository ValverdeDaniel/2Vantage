import { describe, expect, it } from 'vitest';
import { geometryForOffsets } from './pdfGeometry';
import { extractPageText, findHighlightRanges, norm, valueVariants } from './pdfFind';

/** Synthetic pdf.js text items: [text, x, y] on a page, 10-point type. */
const item = ([str, x, y]) => ({ str, transform: [10, 0, 0, 10, x, y], width: str.length * 5 });
const page = (...items) => extractPageText({ items: items.map(item) });

describe('E23 pdfFind', () => {
  it('prints a stored value the ways a carrier prints it', () => {
    expect(valueVariants('300000')).toContain('$300,000');
    expect(valueVariants('512.5')).toContain('$512.50');
    expect(valueVariants('25')).toEqual([]);
    expect(valueVariants('yes')).toEqual([]);
  });

  it('folds dashes and quotes as the locator does', () => {
    expect(norm('Rate — EE  “Gold”')).toBe('rate - ee "gold"');
  });

  it('boxes the value inside its line and keeps the line as context', () => {
    const { pageText } = page(['Employee only $512.34', 72, 700], ['Family $1,580.47', 72, 684]);
    const match = findHighlightRanges(pageText, 'Employee only $512.34', '512.34');
    expect(pageText.slice(...match.ranges[0])).toBe('$512.34');
    expect(pageText.slice(...match.contextRanges[0])).toBe('employee only $512.34');
  });

  it('never matches inside a longer number', () => {
    const { pageText } = page(['Maximum $1,300,000', 72, 700]);
    expect(findHighlightRanges(pageText, '', '300000')).toBe(null);
  });

  it('picks the plan column by the hint words', () => {
    const { pageText, offsets } = page(
      ['Gold PPO', 200, 720],
      ['Silver HMO', 400, 720],
      ['Deductible', 72, 700],
      ['$1,500', 200, 700],
      ['$1,500', 400, 700],
    );
    const match = findHighlightRanges(pageText, '', '1500', geometryForOffsets(offsets), 'Acme Silver HMO');
    const silver = pageText.lastIndexOf('$1,500');
    expect(match.ranges[0][0]).toBe(silver);
  });

  it('searches a short value only where the snippet pins it', () => {
    const { pageText } = page(['Copay 25', 72, 700], ['Visits 25', 72, 684]);
    const match = findHighlightRanges(pageText, 'Visits 25', '25');
    expect(match.ranges[0][0]).toBe(pageText.lastIndexOf('25'));
    expect(findHighlightRanges(pageText, '', '25')).toBe(null);
  });
});
