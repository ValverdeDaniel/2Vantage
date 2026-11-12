import { useEffect, useState } from 'react';
import { ocrBoxes } from './ocrWords';
import { ocrPage } from './pdfOcr';

const MAX_OCR_WIDTH = 2400; // px; a larger photo is scaled down before OCR

/*
 * Where a value is on an uploaded image (plan.md §10.7; E25, E26; the old ImageViewer's locate effect): browser OCR
 * reads the image once per file (pdfOcr), then the PDF matcher finds the value in what it read. Only draws: the image
 * is never changed and nothing is written. `img` is the loaded <img>, `natural` its size, `scale` how large it is
 * drawn. → {boxes: {main, context}, state: idle | reading | ocr | missing}.
 */
export default function useImageFind({ img, url, natural, scale, find, jumpKey }) {
  const [result, setResult] = useState({ key: '', boxes: { main: [], context: [] }, state: 'idle' });
  const asked = Boolean(find.value || find.snippet);
  const key = [url, find.value, find.snippet, find.hint, jumpKey, scale].join('|');

  useEffect(() => {
    if (!natural || !img.current || !asked) return undefined;
    let cancelled = false;
    (async () => {
      setResult({ key, boxes: { main: [], context: [] }, state: 'reading' });
      try {
        const shrink = Math.min(1, MAX_OCR_WIDTH / natural.w);
        const draw = () => {
          const canvas = document.createElement('canvas');
          canvas.width = Math.round(natural.w * shrink);
          canvas.height = Math.round(natural.h * shrink);
          canvas.getContext('2d').drawImage(img.current, 0, 0, canvas.width, canvas.height);
          return canvas;
        };
        const read = await ocrPage(`image:${url}`, 1, draw);
        if (cancelled) return;
        const boxes = ocrBoxes(read, find, (natural.w * scale) / read.width); // OCR pixels → the image as drawn
        setResult({ key, boxes: boxes || { main: [], context: [] }, state: boxes ? 'ocr' : 'missing' });
      } catch {
        if (!cancelled) setResult({ key, boxes: { main: [], context: [] }, state: 'missing' });
      }
    })();
    return () => {
      cancelled = true;
    };
    // `find` is read through `key`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [natural, key, asked]);

  if (!asked) return { boxes: { main: [], context: [] }, state: 'idle' };
  return result.key === key ? result : { boxes: { main: [], context: [] }, state: 'reading' };
}
