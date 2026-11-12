/*
 * Where a value is printed on a PDF page (plan.md §10.7; E23, E24, D-122, D-164): the old pdfText.js, trimmed to
 * drawing. Whether a value is in the file at all is decided only in Python (the locator, slice 16); this finds the
 * characters to box on a page the viewer already shows. Pure: page text in, character ranges out.
 *
 * `findHighlightRanges(pageText, snippet, value, posAt, hint, {exact})` returns {ranges, contextRanges} or null:
 * `ranges` is the box (the value when it can be pinned down, else the snippet), `contextRanges` the fainter box on
 * its line. The snippet is the reader's line; `hint` (the plan's carrier and name) picks the column on a grid that
 * prints the same figure under several plans; `exact` says the server found the figure once on this page.
 */

// Marks two extractors print differently, folded as the server's locator folds them.
const DASH_CODES = [0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212];
const QUOTE_CODES = [0x2018, 0x2019, 0x201a, 0x201b, 0x2032];
const DQUOTE_CODES = [0x201c, 0x201d, 0x201e, 0x201f, 0x2033];
const charClass = (codes) => new RegExp(`[${String.fromCharCode(...codes)}]`, 'g');
const DASHES = charClass(DASH_CODES);
const QUOTES = charClass(QUOTE_CODES);
const DQUOTES = charClass(DQUOTE_CODES);

/** NFKC, folded dashes and quotes, lower case, one space. */
export const norm = (s) =>
  String(s || '')
    .normalize('NFKC')
    .replace(DASHES, '-')
    .replace(QUOTES, "'")
    .replace(DQUOTES, '"')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();

function occurrences(text, target) {
  const out = [];
  let at = text.indexOf(target);
  while (at !== -1) {
    out.push([at, at + target.length]);
    at = text.indexOf(target, at + 1);
  }
  return out;
}

/** A whole word, never a fragment: "silver" may not match inside "silverscript". */
function boundaryOk(text, hit) {
  const before = text[hit[0] - 1];
  const after = text[hit[1]];
  return !(before !== undefined && /[a-z0-9]/.test(before)) && !(after !== undefined && /[a-z0-9]/.test(after));
}

/** The snippet's occurrences: whole, then its first 60 characters, then its longest run of 3 or more words. */
function snippetOccurrences(pageText, snippet) {
  const target = norm(snippet);
  if (!target) return [];
  let hits = occurrences(pageText, target);
  if (hits.length) return hits;
  const prefix = target.slice(0, 60).trim();
  if (prefix.length >= 8) {
    hits = occurrences(pageText, prefix);
    if (hits.length) return hits;
  }
  const words = target.split(' ').filter(Boolean);
  for (let len = words.length; len >= 3; len -= 1) {
    for (let start = 0; start + len <= words.length; start += 1) {
      hits = occurrences(pageText, words.slice(start, start + len).join(' '));
      if (hits.length) return hits;
    }
  }
  return [];
}

/** A value under three characters ("25", "EE") is everywhere on a rate page: searched only where pinned down. */
const isShort = (value) => {
  const v = norm(value);
  return v.length > 0 && v.length < 3;
};

/** The ways a stored value may be printed: "300000" as "$300,000", "300,000.00"…; "512.5" as "$512.50". */
export function valueVariants(value, { short = false } = {}) {
  const v = norm(value);
  if (!v || v === 'yes' || v === 'no') return [];
  if (v.length < 3 && !short) return [];
  const numeric = v.match(/^\$?\s*(\d[\d,]*)(?:\.(\d+))?$/);
  if (!numeric) return [v];
  const n = Number(numeric[1].replace(/,/g, ''));
  if (!Number.isFinite(n)) return [v];
  const grouped = n.toLocaleString('en-US');
  const plain = String(n);
  const cents = (numeric[2] || '').replace(/0+$/, '');
  let variants;
  if (cents) {
    const fracs = [...new Set([cents.padEnd(2, '0'), cents])];
    variants = fracs.flatMap((f) => [
      `$${grouped}.${f}`,
      `$ ${grouped}.${f}`,
      `${grouped}.${f}`,
      `$${plain}.${f}`,
      `${plain}.${f}`,
    ]);
  } else {
    variants = [
      `$${grouped}.00`,
      `$ ${grouped}.00`,
      `${grouped}.00`,
      `$${grouped}`,
      `$ ${grouped}`,
      grouped,
      `$${plain}`,
      `${plain}.00`,
      plain,
    ];
  }
  return [...new Set(variants)].sort((a, b) => b.length - a.length);
}

const overlaps = (a, b) => a[0] < b[1] && b[0] < a[1];

/** Every printed form's occurrences, never inside a longer number ("300,000" is not in "1,300,000"). */
function valueOccurrences(pageText, value, opts = {}) {
  const accepted = [];
  for (const variant of valueVariants(value, opts)) {
    for (const hit of occurrences(pageText, variant)) {
      if (accepted.some((a) => overlaps(a, hit))) continue;
      if (/\d$/.test(variant)) {
        const before = pageText[hit[0] - 1];
        const after = pageText[hit[1]];
        const after2 = pageText[hit[1] + 1];
        if (before !== undefined && /[\d$,.]/.test(before)) continue;
        if (after !== undefined && /\d/.test(after)) continue;
        if (after !== undefined && /[,.]/.test(after) && after2 !== undefined && /\d/.test(after2)) continue;
      } else if (!boundaryOk(pageText, hit)) {
        continue;
      }
      accepted.push(hit);
    }
  }
  return accepted.sort((a, b) => a[0] - b[0]);
}

/** Keep the value hits nearest the hint's words across the page: the plan's own column. */
function byColumn(pageText, value, values, hint, center, rowTol) {
  const valueWords = new Set(norm(value).split(' '));
  const words = [...new Set(norm(hint).split(/[^a-z0-9]+/).filter((w) => w.length >= 3 && !valueWords.has(w)))];
  const hits = words
    .map((w) => occurrences(pageText, w).filter((h) => boundaryOk(pageText, h)).map(center).filter(Boolean))
    .filter((list) => list.length);
  if (!hits.length) return values;
  const dx = (v) => {
    const cv = center(v);
    if (!cv) return Infinity;
    return hits.reduce((sum, list) => sum + Math.min(...list.map((ch) => Math.abs(ch.x - cv.x))), 0) / hits.length;
  };
  const dxs = values.map(dx);
  const min = Math.min(...dxs);
  return Number.isFinite(min) ? values.filter((_v, i) => dxs[i] <= min + rowTol * 3) : values;
}

/** With no snippet on the page, the hit with the most snippet words on its printed row. */
function bySnippetWords(pageText, snippet, value, values, center, posAt) {
  const rowTol = posAt.rowTol || 6;
  const radius = posAt.radius || 150;
  const valueWords = new Set(norm(value).split(' '));
  const words = [...new Set(norm(snippet).split(' ').filter((w) => w.length >= 3 && !valueWords.has(w)))];
  const wordHits = words
    .map((w) => occurrences(pageText, w).filter((h) => boundaryOk(pageText, h)))
    .filter((list) => list.length);
  let pick = values[0];
  let best = -1;
  for (const v of values) {
    const cv = center(v);
    if (!cv) continue;
    let score = 0;
    for (const list of wordHits) {
      let credit = 0;
      for (const h of list) {
        const ch = center(h);
        if (!ch) continue;
        if (Math.abs(ch.y - cv.y) < rowTol) {
          credit = 1;
          break;
        }
        if (Math.hypot(ch.x - cv.x, ch.y - cv.y) < radius) credit = Math.max(credit, 0.5);
      }
      score += credit;
    }
    if (score > best) {
      best = score;
      pick = v;
    }
  }
  return pick;
}

export function findHighlightRanges(pageText, snippet, value = '', posAt = null, hint = '', { exact = false } = {}) {
  const labels = snippetOccurrences(pageText, snippet);
  const short = isShort(value);
  let values = valueOccurrences(pageText, value, { short: short && (exact || labels.length > 0) });
  if (short && !exact) values = values.filter((v) => labels.some((l) => v[0] >= l[0] && v[1] <= l[1]));
  if (!labels.length && !values.length) return null;
  if (!values.length) return { ranges: [labels[0]], contextRanges: [] };

  const center = (r) => (posAt ? posAt(Math.floor((r[0] + r[1]) / 2)) : null);
  // Row first: the same printed row beats horizontal closeness; the stream gap without geometry.
  const pairDist = (l, v) => {
    const cl = center(l);
    const cv = center(v);
    if (cl && cv) return Math.abs(cl.y - cv.y) * 8 + Math.abs(cl.x - cv.x);
    return overlaps(l, v) ? 0 : Math.max(l[0] - v[1], v[0] - l[1]);
  };
  if (posAt && hint && values.length > 1) values = byColumn(pageText, value, values, hint, center, posAt.rowTol || 6);

  if (labels.length) {
    let inside = null;
    for (const l of labels) {
      for (const v of values) {
        if (v[0] >= l[0] && v[1] <= l[1]) {
          const d = pairDist(l, v);
          if (!inside || d < inside.d) inside = { l, v, d };
        }
      }
    }
    if (inside) return { ranges: [inside.v], contextRanges: [inside.l] };
    let best = null;
    for (const l of labels) {
      for (const v of values) {
        const gap = overlaps(l, v) ? 0 : Math.max(l[0] - v[1], v[0] - l[1]);
        const d = pairDist(l, v);
        if (!best || d < best.d || (d === best.d && l[0] < best.l[0])) best = { l, v, gap, d };
      }
    }
    if (best.gap <= 1) {
      return { ranges: [[Math.min(best.l[0], best.v[0]), Math.max(best.l[1], best.v[1])]], contextRanges: [] };
    }
    return { ranges: [best.v], contextRanges: [best.l] };
  }
  if (!posAt || values.length === 1) return { ranges: [values[0]], contextRanges: [] };
  return { ranges: [bySnippetWords(pageText, snippet, value, values, center, posAt)], contextRanges: [] };
}

/** A page's text items as one normalized string, with each item's character offsets. */
export function extractPageText(textContent) {
  let pageText = '';
  const offsets = [];
  (textContent?.items || []).forEach((item) => {
    const text = norm(item.str);
    if (!text) return;
    const start = pageText ? pageText.length + 1 : 0;
    pageText = pageText ? `${pageText} ${text}` : text;
    const family = textContent.styles?.[item.fontName]?.fontFamily || '';
    offsets.push({ start, end: pageText.length, item, family });
  });
  return { pageText, offsets };
}
