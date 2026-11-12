/*
 * What Work with Claude is told the Export viewer shows (plan.md §10.6; J120; the old AdvisorTab getPage's `export`
 * branch at 891f1b3, which made the server rebuild the preview every turn, J.5 B21). Simplify: the browser sends the
 * viewer's state with the message — the file, the slide or tab on screen and how each plan set's table fitted — and the
 * server (`proposals/viewer/turn.py`) only puts it in words. Titles and row labels only: nothing about a person. Pure.
 */

/** The deck view's state: {file, slide: {n, title}, slides, draft, paper?, fits: [...]}. */
export function deckState({ file, slides, index, paper, draft }) {
  const slide = index >= 0 ? slides[index] : null;
  return {
    file,
    slide: slide ? { n: slide.n, title: slide.title } : null,
    slides: slides.length,
    draft: Boolean(draft),
    ...(file === 'paper' && paper ? { paper: { scale: paper.scale, sheet: paper.sheet } } : {}),
    fits: slides
      .filter((s) => s.kind === 'table' && !s.continued && s.fit)
      .map((s) => ({
        n: s.n,
        title: s.title,
        outcome: s.fit.outcome,
        size: s.fit.size,
        floor: s.fit.floor,
        slides: s.fit.slides,
        money_slide: s.fit.money_slide,
        tall_rows: (s.fit.tall_rows || []).map((row) => row.label),
      })),
  };
}

/** The Excel view's state: the tab on screen. */
export const workbookState = (tab) => ({ file: 'excel', tab: tab || '' });
