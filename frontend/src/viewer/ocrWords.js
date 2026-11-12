import { findHighlightRanges, norm } from './pdfFind';

/*
 * What browser OCR read on a scanned page or an image, in the shape the matcher reads (plan.md §10.7; E25; the old
 * pdfOcr.js and pdfText.geometryForOcrEntries). Pure: tesseract.js's blocks in; one normalized page text with each
 * word's character offsets and pixel box out, then where a character sits and the boxes for a range. OCR only draws:
 * nothing here says whether a value is in the file (the server's locator calls a scanned page "check by eye").
 */

/** {pageText, entries: [{start, end, bbox, line}]} from tesseract's blocks → paragraphs → lines → words. */
export function flattenOcr(blocks) {
  let pageText = '';
  const entries = [];
  let lineNo = 0;
  for (const block of blocks || []) {
    for (const paragraph of block.paragraphs || []) {
      for (const line of paragraph.lines || []) {
        lineNo += 1;
        for (const word of line.words || []) {
          const text = norm(word.text);
          if (!text) continue;
          const start = pageText ? pageText.length + 1 : 0;
          pageText = pageText ? `${pageText} ${text}` : text;
          entries.push({ start, end: pageText.length, bbox: word.bbox, line: lineNo });
        }
      }
    }
  }
  return { pageText, entries };
}

/** posAt(charIndex) -> {x, y}, the middle of the word holding it, in OCR pixels; `rowTol` and `radius` ride on it. */
export function geometryForOcrEntries(entries) {
  if (!entries?.length) return null;
  const posAt = (i) => {
    let entry = null;
    for (const o of entries) {
      if (i < o.start) break;
      entry = o;
      if (i < o.end) break;
    }
    const b = (entry || entries[0]).bbox;
    return { x: (b.x0 + b.x1) / 2, y: (b.y0 + b.y1) / 2 };
  };
  const heights = entries
    .map((o) => o.bbox.y1 - o.bbox.y0)
    .filter((h) => h > 0)
    .sort((a, b) => a - b);
  const h = heights.length ? heights[Math.floor(heights.length / 2)] : 24;
  posAt.rowTol = h * 0.6;
  posAt.radius = h * 12;
  return posAt;
}

/**
 * Boxes (CSS px) for a character range: the words it covers, merged into one box per printed line, so a label and its
 * value on one line are one box and a range across two lines is two. `scale` turns OCR pixels into CSS pixels.
 */
export function ocrRectsForRange(entries, range, scale) {
  const [start, end] = range;
  const byLine = new Map();
  for (const { start: s, end: e, bbox, line } of entries) {
    if (e <= start || s >= end) continue;
    const box = byLine.get(line);
    if (box) {
      box.x0 = Math.min(box.x0, bbox.x0);
      box.y0 = Math.min(box.y0, bbox.y0);
      box.x1 = Math.max(box.x1, bbox.x1);
      box.y1 = Math.max(box.y1, bbox.y1);
    } else {
      byLine.set(line, { ...bbox });
    }
  }
  return [...byLine.values()].map((b) => ({
    left: b.x0 * scale,
    top: b.y0 * scale,
    width: (b.x1 - b.x0) * scale,
    height: (b.y1 - b.y0) * scale,
  }));
}

/**
 * The boxes for `find` ({value, snippet, hint}) on what OCR read, in CSS px (`scale`: OCR pixels → CSS pixels), or
 * null when the page does not print it as OCR read it. The same matcher as a PDF's text layer (pdfFind).
 */
export function ocrBoxes(read, find, scale) {
  const posAt = geometryForOcrEntries(read.entries);
  const match = findHighlightRanges(read.pageText, find.snippet, find.value, posAt, find.hint);
  if (!match) return null;
  const boxes = (ranges) => ranges.flatMap((range) => ocrRectsForRange(read.entries, range, scale));
  return { main: boxes(match.ranges), context: boxes(match.contextRanges || []) };
}
