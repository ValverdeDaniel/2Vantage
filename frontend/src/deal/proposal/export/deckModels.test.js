import { describe, expect, it } from 'vitest';
import {
  aboutWords,
  DECK_FILES,
  fitHead,
  fitVerdict,
  jumpsOf,
  paperWords,
  printedPt,
  resolveIndex,
  selectionAt,
  stepTo,
} from './deckModel';
import { previewOf } from './exportFiles';
import { deckState, workbookState } from './viewerState';

const fit = (extra = {}) => ({ outcome: 'fits', size: 9, floor: 8, slides: [3], money_slide: 3, tall_rows: [], ...extra });
const SLIDES = [
  { n: 1, title: 'Golden (synthetic)', kind: 'cover', line: null, continued: false, notes: [], fit: null },
  { n: 2, title: 'Dental — Delta', kind: 'table', line: 'dental', continued: false, notes: ['Why'], fit: fit({ slides: [2], money_slide: 2 }) },
  { n: 3, title: 'Medical — Aetna', kind: 'table', line: 'medical', continued: false, notes: [], fit: fit() },
  { n: 4, title: 'Medical — Aetna (continued)', kind: 'table', line: 'medical', continued: true, notes: [], fit: null },
  { n: 5, title: 'Thank you', kind: 'cover', line: null, continued: false, notes: [], fit: null },
];

describe('J108 J109 the slide on screen', () => {
  it('opens on the first Medical plan set, else the first plan set, else the first slide', () => {
    expect(resolveIndex(SLIDES, null)).toBe(2);
    expect(resolveIndex(SLIDES.filter((s) => s.line !== 'medical'), null)).toBe(1);
    expect(resolveIndex([SLIDES[0], SLIDES[4]], null)).toBe(0);
    expect(resolveIndex([], null)).toBe(-1);
  });

  it('keeps the slide picked by title and position across a rebuild that adds slides before it', () => {
    const picked = selectionAt(SLIDES, 4);
    expect(picked).toEqual({ title: 'Thank you', nth: 0, index: 4 });
    const rebuilt = [SLIDES[0], { ...SLIDES[1], n: 2 }, { n: 3, title: 'New page', kind: 'page' }, ...SLIDES.slice(2)];
    expect(resolveIndex(rebuilt, picked)).toBe(5);
  });

  it('falls back to the same place when the title is gone, held to the last slide', () => {
    expect(resolveIndex(SLIDES, { title: 'Gone', nth: 0, index: 3 })).toBe(3);
    expect(resolveIndex(SLIDES, { title: 'Gone', nth: 0, index: 40 })).toBe(4);
  });

  it('J58 opens on the line asked for, its first plan set', () => {
    expect(resolveIndex(SLIDES, { line: 'dental' })).toBe(1);
    expect(resolveIndex(SLIDES, { line: 'vision' })).toBe(2);
  });

  it('steps with the arrows, PgUp/PgDn, Home and End, held at the ends', () => {
    expect(stepTo('ArrowRight', 1, 5)).toBe(2);
    expect(stepTo('PageUp', 1, 5)).toBe(0);
    expect(stepTo('ArrowLeft', 0, 5)).toBe(0);
    expect(stepTo('End', 1, 5)).toBe(4);
    expect(stepTo('Home', 3, 5)).toBe(0);
    expect(stepTo('a', 3, 5)).toBeNull();
  });
});

describe('J110 the fit report', () => {
  it('says how a table fitted, its level and its tall rows', () => {
    expect(fitVerdict(fit(), 'slide')).toEqual({ level: 'ok', words: 'Fits on one slide at 9 pt', tall: [] });
    expect(fitVerdict(fit({ size: 8 }), 'page').words).toBe('Fits on one page at 8 pt, the smallest type');
    const notes = fitVerdict(fit({ outcome: 'notes_follow', slides: [3, 4] }));
    expect(notes).toMatchObject({ level: 'warn', words: 'The table fits on one slide at 9 pt; the notes under it moved to slide 4' });
    const ran = fitVerdict(fit({ outcome: 'runs_on', size: 8, slides: [3, 4], money_slide: 4 }));
    expect(ran.level).toBe('bad');
    expect(ran.words).toBe(
      'Runs onto 2 slides, to slide 4, even at 8 pt · the rates and totals start on slide 4, apart from the benefits',
    );
    const tall = fitVerdict(fit({ tall_rows: [{ label: 'Office visits', lines: 3 }] }));
    expect(tall).toMatchObject({ level: 'warn', tall: ['Office visits (3 lines)'] });
    expect(fitVerdict(null)).toBeNull();
  });

  it('reads a continued slide as its plan set, and jumps to every plan set with its verdict', () => {
    expect(fitHead(SLIDES, 3)).toBe(2);
    expect(fitHead(SLIDES, 4)).toBe(-1);
    expect(jumpsOf(SLIDES, 'slide').map((s) => [s.i, s.verdict.level])).toEqual([
      [1, 'ok'],
      [2, 'ok'],
    ]);
  });
});

describe('J114 J115 Paper and the page files', () => {
  const paper = { scale: 75, sheet: 'landscape', as_is: false, inner: 0.9091 };

  it('says a table’s type as it prints: 9 pt prints at 6.8 pt', () => {
    expect(printedPt(9, 75)).toBe('6.8 pt');
    expect(paperWords(paper, fit())).toBe(
      'Prints on US Letter landscape at 75%, inside a half-inch margin. This table’s 9 pt type prints at 6.8 pt.',
    );
    expect(paperWords(paper, null)).toBe('Prints on US Letter landscape at 75%, inside a half-inch margin.');
    expect(paperWords({ ...paper, as_is: true }, null)).toMatch(/at 100%/);
  });

  it('gives each page file its downloads, Paper its Print… and Letter PDF, all from the one deck build', () => {
    expect(DECK_FILES.powerpoint.downloads.map((d) => d.path)).toEqual(['pptx']);
    expect(DECK_FILES.pdf.downloads.map((d) => d.path)).toEqual(['pdf']);
    expect(DECK_FILES.paper.downloads.map((d) => [d.label, d.path, Boolean(d.print)])).toEqual([
      ['Print…', 'letter', true],
      ['⬇ Download Letter PDF', 'letter', false],
    ]);
    expect(['powerpoint', 'pdf', 'paper'].map(previewOf)).toEqual(['deck', 'deck', 'deck']);
    expect(previewOf('excel')).toBe('workbook');
    expect(aboutWords('powerpoint', paper, { chart: true })).toMatch(/this slide’s premium chart is drawn as bars here/);
    expect(aboutWords('paper', paper, null)).toMatch(/scaled to 75%/);
  });
});

describe('J120 what Claude is told the viewer shows', () => {
  it('sends the file, the slide on screen, the count and each plan set’s fit, nothing else', () => {
    const told = deckState({ file: 'paper', slides: SLIDES, index: 3, paper: { scale: 75, sheet: 'landscape', inner: 1 }, draft: true });
    expect(told).toEqual({
      file: 'paper',
      slide: { n: 4, title: 'Medical — Aetna (continued)' },
      slides: 5,
      draft: true,
      paper: { scale: 75, sheet: 'landscape' },
      fits: [
        { n: 2, title: 'Dental — Delta', outcome: 'fits', size: 9, floor: 8, slides: [2], money_slide: 2, tall_rows: [] },
        { n: 3, title: 'Medical — Aetna', outcome: 'fits', size: 9, floor: 8, slides: [3], money_slide: 3, tall_rows: [] },
      ],
    });
    expect(deckState({ file: 'powerpoint', slides: SLIDES, index: 0, paper: {}, draft: true }).paper).toBeUndefined();
    expect(workbookState('Dental')).toEqual({ file: 'excel', tab: 'Dental' });
  });
});
