import { useEffect, useState } from 'react';
import cx from '../../../ui/cx';
import PageCanvas from './PageCanvas';

// Paper: the share of the Letter sheet's width a 16:9 page takes when the server has not said (720 of 792 pt).
const PAPER_INNER = 720 / 792;

/** The width of a node that mounts later (a callback ref's node), followed as the window resizes. */
function useWidth(node) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!node) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(node);
    return () => observer.disconnect();
  }, [node]);
  return width;
}

/*
 * The page on the stage (plan.md §8.14, §9.7; J109, J114; the old ExportViewer stage at 891f1b3, D-196): a slide at
 * the stage's width, or, on Paper, the page on its US Letter sheet as it prints — the sheet 11 × 8.5, the page at the
 * share of its width the server's `paper.inner` says (75% of the slide inside a half-inch margin), centred both ways.
 */
export default function PaperFrame({ doc, slide, paper, onPainted }) {
  const [node, setNode] = useState(null);
  const width = useWidth(node);
  const drawn = paper ? Math.floor(width * (paper.inner || PAPER_INNER)) : width;
  return (
    <div className={cx('bnf-xv-slide', paper && 'bnf-xv-paper')} ref={setNode} data-frame={paper ? 'paper' : 'slide'}>
      {slide && <PageCanvas doc={doc} number={slide.n} width={drawn} onPainted={onPainted} />}
    </div>
  );
}
