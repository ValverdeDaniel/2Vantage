import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useProposal } from '../../../api/proposals';
import cx from '../../../ui/cx';
import { publish } from '../../shared/viewerBridge';
import DeckDownloads from './DeckDownloads';
import { aboutWords, deckFile, fitHead, jumpsOf, paperWords, resolveIndex, selectionAt, stepTo } from './deckModel';
import { builtWords, previewOf } from './exportFiles';
import FitReport from './FitReport';
import NotPrinting from './NotPrinting';
import PaperFrame from './PaperFrame';
import SlideRail from './SlideRail';
import useDeckDocument from './useDeckDocument';
import usePreviewCopy from './usePreviewCopy';
import { deckState } from './viewerState';
import ViewerBar from './ViewerBar';

/*
 * The Export viewer's deck view (plan.md §8.14; J107–J115, J120; the old ExportViewer DeckViewer at 891f1b3, D-193,
 * D-196): the client PowerPoint's slides, the PDF's pages or those pages on US Letter (`file`), as they would download
 * now. One server build serves the three (`proposals/viewer/deck.py`: the PDF's bytes and the page log), drawn here with
 * pdf.js, so switching between them never builds again and stays on the same slide. It opens on the first Medical plan
 * set and keeps to the slide picked across rebuilds, by title and position (`selected`, held by the Advisor); ←→,
 * PgUp/PgDn and Home/End step; the rail's thumbnails and the Jump chips (with fit dots) go straight to a slide; the fit
 * report sits above a plan set; the PowerPoint shows its speaker notes; Paper sets each page on its Letter sheet and
 * says the type as it prints. What is on screen is published for Work with Claude (J120, `viewerState`). The root says
 * what it is doing for the walks: `data-render` loading | ready | error, `data-viewer-page`, `data-viewer-file`.
 */
export default function DeckViewer({ dealId, file, chips, selected, onSelect, onGoBuild }) {
  const what = deckFile(file);
  const { noun } = what;
  const Noun = noun[0].toUpperCase() + noun.slice(1);
  const copy = usePreviewCopy(dealId, { file: previewOf(file), tab: '', shown: true });
  const builder = useProposal(dealId);
  const data = copy.data;
  const slides = useMemo(() => data?.slides || [], [data]);
  const paper = data?.paper || null;
  const { doc, failed: unreadable } = useDeckDocument(data?.pdf);
  const index = resolveIndex(slides, selected);
  const slide = index >= 0 ? slides[index] : null;
  const [painted, setPainted] = useState({ doc: null, n: 0 });
  const onPainted = useCallback((drawn, n) => setPainted({ doc: drawn, n }), []);
  const rootRef = useRef(null);

  // The arrows work from the moment the view opens.
  useEffect(() => {
    rootRef.current?.focus({ preventScroll: true });
  }, []);

  const jumps = useMemo(() => jumpsOf(slides, noun), [slides, noun]);
  const verdicts = useMemo(() => Object.fromEntries(jumps.map((s) => [s.i, s.verdict])), [jumps]);
  const head = index >= 0 ? fitHead(slides, index) : -1;
  const sheet = file === 'paper' && paper && !paper.as_is ? paper : null;

  const told = useMemo(
    () => (data ? deckState({ file, slides, index, paper, draft: data.draft }) : null),
    [data, file, slides, index, paper],
  );
  useEffect(() => (told ? publish(dealId, told) : undefined), [dealId, told]);

  const go = (next) => {
    if (next >= 0 && next < slides.length && next !== index) onSelect(selectionAt(slides, next));
  };
  const onKeyDown = (event) => {
    // Typing is never steering; a button keeps its own Space and Enter.
    if (event.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
    const next = stepTo(event.key, index, slides.length);
    if (next === null) return;
    event.preventDefault();
    go(next);
  };

  let status = builtWords(data?.built_at, slides.length, noun);
  if (copy.building) status = data ? 'Rebuilding…' : `Building the ${noun}s…`;
  else if (copy.stale) status = 'The deal changed since this copy';
  const ready = Boolean(slide) && painted.doc === doc && painted.n === slide.n;
  const renderState = copy.refused || unreadable ? 'error' : ready ? 'ready' : 'loading';

  return (
    <div
      className="bnf-xv"
      data-render={renderState}
      data-viewer-file={file}
      data-viewer-page={slide ? slide.n : undefined}
      ref={rootRef}
      tabIndex={-1}
      onKeyDown={onKeyDown}
    >
      <ViewerBar
        chips={chips}
        draft={data?.draft}
        status={status}
        building={copy.building}
        onRefresh={copy.refresh}
        download={<DeckDownloads dealId={dealId} what={what} />}
      />

      {jumps.length > 0 && (
        <div className="bnf-xv-jump" role="group" aria-label="Jump to">
          <span className="bnf-xv-jump-label">Jump to</span>
          {jumps.map((s) => (
            <button
              key={s.i}
              type="button"
              className={cx('bnf-xv-chip', s.i === index && 'bnf-xv-chip-on')}
              onClick={() => go(s.i)}
              title={s.verdict?.words}
            >
              {s.verdict && s.verdict.level !== 'ok' && (
                <span className={`bnf-xv-dot bnf-xv-dot-${s.verdict.level}`} aria-hidden="true" />
              )}
              {s.title}
            </button>
          ))}
        </div>
      )}

      <NotPrinting ledger={builder.data?.ledger} pages={builder.data?.output?.pages} onGoBuild={onGoBuild} />

      {copy.failed && data && (
        <div className="bnf-xv-notice bnf-xv-notice-warn" role="status">
          {copy.failed} This is the last copy.{' '}
          <button type="button" className="bnf-refresh-retry" onClick={copy.refresh}>
            Try again
          </button>
        </div>
      )}
      {copy.refused && (
        <div className="bnf-xv-notice bnf-xv-notice-warn" role="alert">
          {copy.refused} The {what.name} download says the same.
        </div>
      )}
      {!data && !copy.refused && (
        <div className="bnf-xv-notice">
          {copy.failed ? (
            <>
              {copy.failed}{' '}
              <button type="button" className="bnf-refresh-retry" onClick={copy.refresh}>
                Try again
              </button>
            </>
          ) : (
            what.building
          )}
        </div>
      )}
      {unreadable && (
        <div className="bnf-xv-notice bnf-xv-notice-warn" role="alert">
          The {noun}s could not be drawn in this browser. Download the {what.name} to see them.
        </div>
      )}

      {data && slides.length > 0 && (
        <div className="bnf-xv-body">
          <SlideRail slides={slides} index={index} doc={doc} verdicts={verdicts} noun={noun} onGo={go} />
          <div className="bnf-xv-stage">
            <FitReport verdict={head >= 0 ? verdicts[head] : null} />
            {file === 'paper' && paper && (
              <div className="bnf-xv-paperline" role="status">
                {paperWords(paper, head >= 0 ? slides[head].fit : null)}
              </div>
            )}
            <PaperFrame doc={doc} slide={slide} paper={sheet} onPainted={onPainted} />
            <div className="bnf-xv-nav">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => go(index - 1)}
                disabled={index <= 0}
                aria-label={`Previous ${noun}`}
              >
                ‹
              </button>
              <span>
                {Noun} {slide ? slide.n : 0} of {slides.length}
                {slide?.title ? ` · ${slide.title}` : ''}
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => go(index + 1)}
                disabled={index >= slides.length - 1}
                aria-label={`Next ${noun}`}
              >
                ›
              </button>
            </div>
            {/* Speaker notes are the deck's alone: the PDF has none (J111). */}
            {what.notes && slide?.notes?.length > 0 && (
              <div className="bnf-xv-notes">
                <div className="bnf-xv-notes-label">Speaker notes</div>
                {slide.notes.map((note, i) => (
                  <p key={i}>{note}</p>
                ))}
              </div>
            )}
            <div className="bnf-xv-about">{aboutWords(file, paper, slide)}</div>
          </div>
        </div>
      )}
    </div>
  );
}
