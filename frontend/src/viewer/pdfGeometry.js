/*
 * Where text sits on a PDF page (plan.md §10.7; E23, D-164): the geometry half of the old pdfText.js and PdfViewer's
 * box maker. Pure: pdf.js text items and a viewport transform in, points and rectangles out.
 */

/** pdf.js's Util.transform: the product of two 2-D affine matrices [a, b, c, d, e, f]. */
export function transform(m1, m2) {
  return [
    m1[0] * m2[0] + m1[2] * m2[1],
    m1[1] * m2[0] + m1[3] * m2[1],
    m1[0] * m2[2] + m1[2] * m2[3],
    m1[1] * m2[2] + m1[3] * m2[3],
    m1[0] * m2[4] + m1[2] * m2[5] + m1[4],
    m1[1] * m2[4] + m1[3] * m2[5] + m1[5],
  ];
}

const isRotated = (t) => Math.abs(t[1]) > 0.01 || Math.abs(t[2]) > 0.01;

/**
 * posAt(charIndex) -> {x, y} on the page (PDF units), interpolated inside the covering text item, so candidates are
 * compared by where they sit on the page rather than by their place in the item stream. On a page printed landscape
 * and rotated (most items rotated), reading coordinates are reported, so "same row" means what it meant in print.
 * `rowTol` and `radius` ride on the function, in the page's units.
 */
export function geometryForOffsets(offsets) {
  if (!offsets?.length) return null;
  const rotatedPage = offsets.filter((o) => isRotated(o.item.transform)).length > offsets.length / 2;
  const posAt = (i) => {
    let entry = null;
    for (const o of offsets) {
      if (i < o.start) break;
      entry = o;
      if (i < o.end) break;
    }
    entry = entry || offsets[0];
    const frac = Math.min(1, Math.max(0, (i - entry.start) / Math.max(1, entry.end - entry.start)));
    const t = entry.item.transform;
    const w = entry.item.width || 0;
    const [px, py] = isRotated(t) ? [t[4], t[5] + w * frac * (Math.sign(t[1]) || 1)] : [t[4] + w * frac, t[5]];
    return rotatedPage ? { x: py, y: px } : { x: px, y: py };
  };
  const heights = offsets
    .map((o) => Math.hypot(o.item.transform[2], o.item.transform[3]))
    .filter((h) => h > 0)
    .sort((a, b) => a - b);
  const h = heights.length ? heights[Math.floor(heights.length / 2)] : 10;
  posAt.rowTol = h * 0.6;
  posAt.radius = h * 12;
  return posAt;
}

/**
 * Boxes (CSS px, page-relative) for a character range: one per covered text item, an item partly covered sliced by
 * `fraction(entry, at)` (its font's metrics in the browser; by character count otherwise). Built from the device
 * transform's basis vectors, so rotated text gets a correctly oriented box.
 */
export function rectsForRange(offsets, range, viewport, fraction = countedFraction) {
  const [start, end] = range;
  const rects = [];
  offsets.forEach((entry) => {
    const { start: s, end: e, item } = entry;
    if (e <= start || s >= end || !item.str.trim()) return;
    const tx = transform(viewport.transform, item.transform);
    const f0 = fraction(entry, start - s);
    const f1 = fraction(entry, end - s);
    const w = item.width * viewport.scale;
    const advance = Math.hypot(tx[0], tx[1]) || 1;
    const ux = tx[0] / advance;
    const uy = tx[1] / advance;
    const x0 = tx[4] + ux * w * f0;
    const y0 = tx[5] + uy * w * f0;
    const x1 = tx[4] + ux * w * f1;
    const y1 = tx[5] + uy * w * f1;
    const xs = [x0, x1, x0 + tx[2], x1 + tx[2]];
    const ys = [y0, y1, y0 + tx[3], y1 + tx[3]];
    const left = Math.min(...xs);
    const top = Math.min(...ys);
    rects.push({
      left,
      top,
      width: Math.max(2, Math.max(...xs) - left),
      height: Math.max(2, Math.max(...ys) - top),
    });
  });
  return rects;
}

/** How far into a run a character sits, by count. */
export function countedFraction(entry, at) {
  return Math.min(1, Math.max(0, at / Math.max(1, entry.end - entry.start)));
}
