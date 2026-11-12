import { describe, expect, it } from 'vitest';
import { flattenOcr, geometryForOcrEntries, ocrBoxes, ocrRectsForRange } from './ocrWords';

// A scanned SBC's two rows as tesseract.js reads them (synthetic): words with pixel boxes, line by line.
const word = (text, x0, y0, x1, y1) => ({ text, bbox: { x0, y0, x1, y1 } });
const line = (...words) => ({ words });
const BLOCKS = [
  {
    paragraphs: [
      { lines: [line(word('Aetna', 90, 200, 190, 230), word('Choice', 200, 200, 320, 230), word('POS', 330, 200, 400, 230))] },
      {
        lines: [
          line(word('What', 90, 400, 160, 430), word('is', 170, 400, 190, 430), word('the', 200, 400, 250, 430)),
          line(word('deductible?', 90, 440, 280, 470), word('$2,000', 700, 400, 820, 430), word('individual', 830, 400, 1000, 430)),
          line(word('Out-of-pocket', 90, 520, 300, 550), word('$6,000', 700, 520, 820, 550), word('individual', 830, 520, 1000, 550)),
        ],
      },
    ],
  },
];

describe('browser OCR only draws (E25)', () => {
  it('test_E25_flattens_words_into_one_normalized_text_with_offsets', () => {
    const { pageText, entries } = flattenOcr(BLOCKS);
    expect(pageText.startsWith('aetna choice pos what is the deductible? $2,000')).toBe(true);
    const at = entries.find((e) => pageText.slice(e.start, e.end) === '$6,000');
    expect(at.bbox).toEqual({ x0: 700, y0: 520, x1: 820, y1: 550 });
    expect(flattenOcr([]).pageText).toBe('');
  });

  it('test_E25_boxes_the_value_in_css_pixels_on_its_own_line', () => {
    const read = flattenOcr(BLOCKS);
    const boxes = ocrBoxes(read, { value: '6000', snippet: '', hint: 'Aetna Choice POS II 2000' }, 0.5);
    expect(boxes.main).toEqual([{ left: 350, top: 260, width: 60, height: 15 }]);
    expect(ocrBoxes(read, { value: '2000', snippet: '', hint: '' }, 1).main[0].left).toBe(700);
  });

  it('test_E25_a_value_the_scan_does_not_print_draws_nothing', () => {
    const read = flattenOcr(BLOCKS);
    expect(ocrBoxes(read, { value: '7500', snippet: '', hint: '' }, 1)).toBeNull();
    expect(ocrBoxes(read, { value: '25', snippet: '', hint: '' }, 1)).toBeNull(); // short: only inside its line
  });

  it('test_E25_a_range_over_two_lines_is_two_boxes_and_rows_have_a_tolerance', () => {
    const { pageText, entries } = flattenOcr(BLOCKS);
    const start = pageText.indexOf('the');
    const end = pageText.indexOf('$2,000') + 6;
    expect(ocrRectsForRange(entries, [start, end], 1)).toHaveLength(2);
    const posAt = geometryForOcrEntries(entries);
    expect(posAt(pageText.indexOf('$6,000'))).toEqual({ x: 760, y: 535 });
    expect(posAt.rowTol).toBeCloseTo(18);
    expect(geometryForOcrEntries([])).toBeNull();
  });
});
