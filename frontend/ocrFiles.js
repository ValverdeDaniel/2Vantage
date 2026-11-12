import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

/*
 * The browser OCR's own files, served from our origin (plan.md §11.2, E.6; E25, OQ98; slice 65): tesseract.js's
 * worker, its WebAssembly core (the three LSTM builds; the worker picks the one the browser runs) and the English
 * data, under `<base>ocr/` with their own names, which tesseract.js asks for. In development this server answers them;
 * a build writes them beside the SPA's assets, so WhiteNoise serves them under /static/ocr/. The OCR module
 * (src/viewer/pdfOcr.js) names these paths, so the browser never reaches a CDN: nothing leaves our origin.
 */
export const OCR_DIR = 'ocr';

const FILES = {
  'worker.min.js': 'tesseract.js/dist/worker.min.js',
  'tesseract-core-lstm.wasm.js': 'tesseract.js-core/tesseract-core-lstm.wasm.js',
  'tesseract-core-simd-lstm.wasm.js': 'tesseract.js-core/tesseract-core-simd-lstm.wasm.js',
  'tesseract-core-relaxedsimd-lstm.wasm.js': 'tesseract.js-core/tesseract-core-relaxedsimd-lstm.wasm.js',
  'eng.traineddata.gz': '@tesseract.js-data/eng/4.0.0_best_int/eng.traineddata.gz',
};

const read = (name) => readFileSync(fileURLToPath(new URL(`./node_modules/${FILES[name]}`, import.meta.url)));

export default function ocrFiles() {
  let base = '/';
  return {
    name: 'vantage-ocr-files',
    configResolved(config) {
      base = config.base;
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const path = (req.url || '').split('?')[0];
        const prefix = `${base}${OCR_DIR}/`;
        const name = path.startsWith(prefix) ? path.slice(prefix.length) : '';
        if (!FILES[name]) return next();
        res.setHeader('Content-Type', name.endsWith('.js') ? 'text/javascript' : 'application/octet-stream');
        res.end(read(name));
      });
    },
    generateBundle() {
      for (const name of Object.keys(FILES)) {
        this.emitFile({ type: 'asset', fileName: `${OCR_DIR}/${name}`, source: read(name) });
      }
    },
  };
}
