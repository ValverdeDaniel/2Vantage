import { flattenOcr } from './ocrWords';

/*
 * Browser OCR for scanned pages and images (plan.md §10.7, §11.2; E25, OQ98; the old pdfOcr.js): tesseract.js, loaded
 * on first use, one worker for the session. Its worker script, WebAssembly core and English data come from our own
 * origin (`<base>ocr/`, written by frontend/ocrFiles.js), never a CDN, and the page's pixels go only to that worker in
 * this browser. The file is never changed and nothing is written anywhere: OCR only tells the viewer where to draw
 * (the server's locator keeps a scanned page "check by eye").
 */

const OCR_BASE = `${import.meta.env.BASE_URL}ocr`;
const OCR_PATHS = { workerPath: `${OCR_BASE}/worker.min.js`, corePath: OCR_BASE, langPath: OCR_BASE };
const MAX_PAGES = 20; // pages read kept in memory
const OCR_WIDTH = 2000; // px a PDF page is drawn at for OCR

let workerPromise = null;
function ocrWorker() {
  if (!workerPromise) {
    workerPromise = import('tesseract.js').then(({ createWorker }) => createWorker('eng', undefined, OCR_PATHS));
    workerPromise.catch(() => {
      workerPromise = null; // a failed load may be tried again
    });
  }
  return workerPromise;
}

const read = new Map();

/**
 * What OCR reads on one page, once per (`key`, `page`): {pageText, entries, width} (ocrWords.flattenOcr; `width` the
 * picture's, in pixels). `draw()` makes the picture (a canvas) only when the page was not read yet. A page being read
 * is shared by every caller; a failed one may be read again.
 */
export function ocrPage(key, page, draw) {
  const id = `${key}|${page}`;
  if (!read.has(id)) {
    const promise = (async () => {
      const canvas = await draw();
      const worker = await ocrWorker();
      const { data } = await worker.recognize(canvas, {}, { blocks: true, text: false });
      return { ...flattenOcr(data.blocks), width: canvas.width };
    })();
    promise.catch(() => read.delete(id));
    if (read.size >= MAX_PAGES) read.delete(read.keys().next().value);
    read.set(id, promise);
  }
  return read.get(id);
}

/**
 * A PDF page drawn for OCR at its own size, about OCR_WIDTH pixels wide whatever the zoom or the panel's width, so small
 * print on a scan is read as well in a narrow panel as in a wide one (the old app read the canvas on screen).
 */
export async function pageForOcr(pdfPage) {
  const base = pdfPage.getViewport({ scale: 1 });
  const viewport = pdfPage.getViewport({ scale: Math.min(4, Math.max(1, OCR_WIDTH / base.width)) });
  const canvas = document.createElement('canvas');
  canvas.width = Math.floor(viewport.width);
  canvas.height = Math.floor(viewport.height);
  await pdfPage.render({ canvas, canvasContext: canvas.getContext('2d'), viewport }).promise;
  return canvas;
}
