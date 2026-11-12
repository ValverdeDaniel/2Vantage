/*
 * The one pdf.js build (plan.md §3.1, O.3.5; E22): the LEGACY build with its worker bundled by Vite, shared by the
 * Documents viewer and (slice 33) the Export viewer. The modern build calls Promise.try and friends with no polyfill,
 * so on a browser a year or two old its worker never answers (the old app's builder-polish note P1). In production
 * WhiteNoise must serve `.mjs` as JavaScript (E.6, release gate).
 */
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export default pdfjs;
