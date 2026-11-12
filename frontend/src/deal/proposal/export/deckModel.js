/*
 * The deck view's small rules (plan.md §8.14; J108–J111, J114, J115; the old ExportViewer.jsx at 891f1b3): which slide
 * is on screen across rebuilds (J108), where the view opens (J109), the keys that step, the Jump chips and their fit
 * dots, the fit report's words (J110), Paper's line (J114) and each page file's words and downloads (J115). The slides
 * are the server's page log (`proposals/viewer/deck.py`): {n, title, kind: cover | table | page, line, continued,
 * notes, chart, fit}. Pure.
 */

// Each page file of the one deck build: what a page is called, its words while it builds, and its downloads (J115).
// PDF and Paper draw the PDF's own pages, the PowerPoint's slides one for one; only the PowerPoint has speaker notes.
export const DECK_FILES = {
  powerpoint: {
    noun: 'slide',
    name: 'PowerPoint',
    notes: true,
    building: 'Building the slides as the PowerPoint will export them…',
    downloads: [
      { key: 'pptx', label: '⬇ Download PowerPoint', title: 'The same file the builder downloads', path: 'pptx' },
    ],
  },
  pdf: {
    noun: 'page',
    name: 'PDF',
    notes: false,
    building: 'Building the pages as the PDF will download…',
    downloads: [{ key: 'pdf', label: '⬇ Download PDF', title: 'The same file the builder downloads', path: 'pdf' }],
  },
  paper: {
    noun: 'page',
    name: 'Letter PDF',
    notes: false,
    building: 'Building the pages as they will print…',
    downloads: [
      { key: 'print', label: 'Print…', print: true, title: 'These Letter sheets, in the browser’s print dialog', path: 'letter' },
      { key: 'letter', label: '⬇ Download Letter PDF', title: 'The PDF on US Letter, as it prints', path: 'letter' },
    ],
  },
};

export const deckFile = (file) => DECK_FILES[file] || DECK_FILES.powerpoint;

const firstTable = (slides, line) =>
  slides.findIndex((s) => s.kind === 'table' && !s.continued && (line === undefined || s.line === line));

/**
 * The slide asked for (J108, J109): the nth slide with its title, else the same place; a line asked for ("See the
 * slides ▸", J58) is that line's first plan set; else the first Medical plan set, else the first plan set, else the
 * first slide. -1 while there are none.
 */
export function resolveIndex(slides, selected) {
  if (!slides.length) return -1;
  if (selected?.title !== undefined) {
    let seen = 0;
    for (let i = 0; i < slides.length; i += 1) {
      if (slides[i].title === selected.title) {
        if (seen === selected.nth) return i;
        seen += 1;
      }
    }
    if (Number.isInteger(selected.index)) return Math.max(0, Math.min(selected.index, slides.length - 1));
  }
  if (selected?.line) {
    const found = firstTable(slides, selected.line);
    if (found >= 0) return found;
  }
  const medical = firstTable(slides, 'medical');
  if (medical >= 0) return medical;
  const table = firstTable(slides);
  return table >= 0 ? table : 0;
}

/** What is kept of the slide at `index`: its title, which of that title it is, and where it stood. */
export function selectionAt(slides, index) {
  const { title } = slides[index];
  const nth = slides.slice(0, index).filter((s) => s.title === title).length;
  return { title, nth, index };
}

const STEPS = { ArrowLeft: -1, ArrowUp: -1, PageUp: -1, ArrowRight: 1, ArrowDown: 1, PageDown: 1 };

/** The slide a key moves to (←→, ↑↓, PgUp/PgDn, Home/End), held at the ends; null for a key that does not step. */
export function stepTo(key, index, count) {
  let next;
  if (key in STEPS) next = index + STEPS[key];
  else if (key === 'Home') next = 0;
  else if (key === 'End') next = count - 1;
  else return null;
  return Math.max(0, Math.min(next, count - 1));
}

/** The plan set a slide belongs to: its own first slide, back over "(continued)" slides, or -1 when it is not one. */
export function fitHead(slides, index) {
  let i = index;
  while (i > 0 && slides[i].kind === 'table' && slides[i].continued) i -= 1;
  return slides[i]?.kind === 'table' ? i : -1;
}

export const pt = (size) => `${Number(size).toString()} pt`;
/** A type size as it prints at `scale` percent, to a tenth of a point: 9 pt at 75% prints at 6.8 pt. */
export const printedPt = (size, scale) => pt(Math.round((size * scale) / 10) / 10);

/**
 * The fit report's verdict on a plan set (J110): {level: ok | warn | bad, words, tall}. Green fits; amber moved its
 * notes on, sits at the smallest type or has rows over two lines; red ran on, or its rates and totals start on another
 * slide than its benefits (Stephanie's rule). `noun` is the file's: the PDF's pages are the slides.
 */
export function fitVerdict(fit, noun = 'slide') {
  if (!fit) return null;
  const pages = fit.slides || [];
  const first = pages[0];
  const last = pages[pages.length - 1];
  const atFloor = fit.size <= fit.floor;
  const tall = (fit.tall_rows || []).map((row) => `${row.label} (${row.lines} lines)`);
  let level = 'ok';
  let words;
  if (fit.outcome === 'runs_on') {
    level = 'bad';
    words = `Runs onto ${pages.length} ${noun}s, to ${noun} ${last}, even at ${pt(fit.size)}`;
  } else if (fit.outcome === 'notes_follow') {
    level = 'warn';
    words = `The table fits on one ${noun} at ${pt(fit.size)}; the notes under it moved to ${noun} ${pages[1] || first + 1}`;
  } else {
    level = atFloor ? 'warn' : 'ok';
    words = `Fits on one ${noun} at ${pt(fit.size)}${atFloor ? ', the smallest type' : ''}`;
  }
  if (fit.money_slide && fit.money_slide !== first) {
    level = 'bad';
    words += ` · the rates and totals start on ${noun} ${fit.money_slide}, apart from the benefits`;
  }
  if (tall.length && level === 'ok') level = 'warn';
  return { level, words, tall };
}

/** Every plan set's first slide, to reach in one click (the Jump chips), with its verdict: [{...slide, i, verdict}]. */
export function jumpsOf(slides, noun) {
  return slides
    .map((s, i) => ({ ...s, i, verdict: fitVerdict(s.fit, noun) }))
    .filter((s) => s.kind === 'table' && !s.continued);
}

/** Paper's line above the page (J114): the sheet and scale, and on a plan set the table's type as it prints. */
export function paperWords(paper, headFit) {
  if (!paper) return '';
  if (paper.as_is) return 'The PDF is already US Letter, so each page prints as it is, at 100%.';
  const said = `Prints on US Letter ${paper.sheet} at ${paper.scale}%, inside a half-inch margin.`;
  return headFit?.size ? `${said} This table’s ${pt(headFit.size)} type prints at ${printedPt(headFit.size, paper.scale)}.` : said;
}

/** The note under the stage: what this file's pages are, and where the download can differ. */
export function aboutWords(file, paper, slide) {
  if (file === 'pdf') {
    return (
      'The PDF exactly as it downloads. In the Presentation format its pages are the PowerPoint’s slides one for one, ' +
      'so the fit report reads the same. The PDF has no speaker notes.'
    );
  }
  if (file === 'paper') {
    return (
      `The PDF as it prints on US Letter: each 16:9 page is scaled to ${paper?.scale ?? 75}% to fit inside a half-inch ` +
      'margin, and its type with it. Print… and the Letter PDF are exactly these sheets; printing the PDF itself to ' +
      'fit the page comes out close to this.'
    );
  }
  // A chart slide is labelled (J.5 B22): the PowerPoint's chart is native and lays itself out.
  const chart = slide?.chart
    ? 'this slide’s premium chart is drawn as bars here and as a native chart in PowerPoint'
    : 'the premium chart is drawn as bars here and as a chart in PowerPoint';
  return (
    'The slides as the PowerPoint lays them out. PowerPoint wraps text itself, so a long cell can sit a little ' +
    `differently there; ${chart}.`
  );
}
