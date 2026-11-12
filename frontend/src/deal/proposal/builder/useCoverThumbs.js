import { useCallback, useEffect, useRef, useState } from 'react';

// pdf.js loads only when the Cover card first draws its tiles (it is the Documents viewer's lazy chunk).
const loadPdfjs = () => import('../../../viewer/pdfjs').then((module) => module.default);

const THUMB_WIDTH = 300; // drawn at twice the tile's 150 px, so it stays sharp

async function drawPage(doc, number) {
  const page = await doc.getPage(number);
  const base = page.getViewport({ scale: 1 });
  const viewport = page.getViewport({ scale: THUMB_WIDTH / base.width });
  const canvas = document.createElement('canvas');
  canvas.width = Math.floor(viewport.width);
  canvas.height = Math.floor(viewport.height);
  await page.render({ canvas, canvasContext: canvas.getContext('2d'), viewport }).promise;
  return canvas.toDataURL('image/png');
}

/*
 * The Cover card's tiles, drawn from the server's tile PDF with the one pdf.js build (plan.md §8.14; J32; the old
 * CoverPicker's PdfPagesPreview at 891f1b3). Each tile shows as soon as its page is drawn. A tile that could not be
 * drawn says so and offers its own Retry (J.5 B19: the old one needed a page reload); a document that would not open
 * marks every tile, and Retry opens it again. → {thumbs: [data URL | undefined], failed: Set of tile indexes, retry}.
 */
export default function useCoverThumbs(data) {
  // Each answer is tagged with the bytes it drew, so a new PDF never shows the last one's tiles.
  const [state, setState] = useState({ source: null, thumbs: [], failed: new Set() });
  const [attempt, setAttempt] = useState(0);
  const docRef = useRef(null);

  const drawOne = useCallback(async (source, doc, index) => {
    const mine = (now) => (now.source === source ? now : { source, thumbs: [], failed: new Set() });
    try {
      const url = await drawPage(doc, index + 1);
      setState((now) => {
        const held = mine(now);
        const thumbs = [...held.thumbs];
        thumbs[index] = url;
        const failed = new Set(held.failed);
        failed.delete(index);
        return { source, thumbs, failed };
      });
    } catch {
      setState((now) => ({ ...mine(now), failed: new Set([...mine(now).failed, index]) }));
    }
  }, []);

  useEffect(() => {
    if (!data) return undefined;
    let cancelled = false;
    let task = null;
    loadPdfjs()
      .then((pdfjs) => {
        if (cancelled) throw new Error('superseded');
        task = pdfjs.getDocument({ data: new Uint8Array(data.slice(0)) });
        return task.promise;
      })
      .then(async (doc) => {
        if (cancelled) return;
        docRef.current = { source: data, doc };
        setState((now) => (now.source === data ? { ...now, failed: new Set() } : now)); // opened this time
        for (let index = 0; index < doc.numPages && !cancelled; index += 1) await drawOne(data, doc, index);
      })
      .catch(() => {
        if (!cancelled) setState({ source: data, thumbs: [], failed: new Set(['all']) });
      });
    return () => {
      cancelled = true;
      docRef.current = null;
      task?.destroy();
    };
  }, [data, attempt, drawOne]);

  const retry = useCallback(
    (index) => {
      if (docRef.current && index !== 'all') drawOne(docRef.current.source, docRef.current.doc, index);
      else setAttempt((n) => n + 1);
    },
    [drawOne],
  );
  const shown = state.source === data ? state : { thumbs: [], failed: new Set() };
  return { thumbs: shown.thumbs, failed: shown.failed, retry };
}
