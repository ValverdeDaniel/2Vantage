import { useEffect, useRef } from 'react';

/*
 * One page of the deck preview drawn at `width` CSS pixels (plan.md §8.14; J109; the old ExportViewer PageCanvas at
 * 891f1b3): drawn off screen first, so the canvas on screen swaps whole and never flashes blank while a new copy draws.
 * `onPainted(doc, number)` says which document's page is on screen (the walks' `data-render` ready).
 */
export default function PageCanvas({ doc, number, width, onPainted }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!doc || !width || !ref.current) return undefined;
    let cancelled = false;
    let task = null;
    (async () => {
      try {
        const page = await doc.getPage(number);
        if (cancelled) return;
        const base = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({ scale: width / base.width });
        const dpr = window.devicePixelRatio || 1;
        const off = document.createElement('canvas');
        off.width = Math.floor(viewport.width * dpr);
        off.height = Math.floor(viewport.height * dpr);
        task = page.render({
          canvas: off,
          canvasContext: off.getContext('2d'),
          viewport,
          transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined,
        });
        await task.promise;
        if (cancelled || !ref.current) return;
        const canvas = ref.current;
        canvas.width = off.width;
        canvas.height = off.height;
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;
        canvas.getContext('2d').drawImage(off, 0, 0);
        onPainted?.(doc, number);
      } catch {
        /* superseded, or the document closed under it */
      }
    })();
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [doc, number, width, onPainted]);
  return <canvas ref={ref} />;
}
