import { lazy, Suspense } from 'react';
import { inlineUrl } from '../api/documents';
import ImageViewer from './ImageViewer';
import SheetViewer from './SheetViewer';

// pdf.js is most of the station's weight: it loads with the first PDF, never with a sheet or an image.
const PdfViewer = lazy(() => import('./PdfViewer'));
const opening = (
  <div className="bb-pdf-loading" role="status">
    Loading document…
  </div>
);

/*
 * One file, shown by its shape (plan.md §8.16; E21, E30): PDF, image, spreadsheet, or "can't be previewed here". The
 * server names the shape (documents/kinds.py `shape_of`), so every type a kind accepts and a viewer reads has one.
 * `find` is the value being shown ({page, cell, value, snippet, hint, exact}); `jumpKey` repeats the same find. Each
 * viewer is keyed by the file, so a new file never shows the last one's pages while it loads.
 */
export default function DocumentViewer({ document, find = {}, jumpKey = 0, onPageChange, onDownload }) {
  if (!document) return null;
  const host = (child) => (
    <div className="bnf-viewer-host" data-viewer-doc={document.id} data-viewer-shape={document.shape || 'none'}>
      {child}
    </div>
  );
  if (document.shape === 'pdf') {
    return host(
      <Suspense fallback={opening}>
        <PdfViewer
          key={document.id}
          url={inlineUrl(document.id)}
          find={find}
          jumpKey={jumpKey}
          onPageChange={onPageChange}
        />
      </Suspense>,
    );
  }
  if (document.shape === 'sheet') {
    return host(<SheetViewer key={document.id} documentId={document.id} find={find} jumpKey={jumpKey} />);
  }
  if (document.shape === 'image') {
    return host(<ImageViewer key={document.id} url={inlineUrl(document.id)} find={find} />);
  }
  const shown = document.display_name || document.original_name;
  return host(
    <div className="bnf-nopreview" data-render="ready" data-find="idle">
      <div className="bb-drop-icon">🗂️</div>
      <div className="bb-drop-filename">{shown}</div>
      <div className="bb-drop-meta">
        {shown !== document.original_name && (
          <>
            File: {document.original_name}
            <br />
          </>
        )}
        This file can&apos;t be previewed here
        {onDownload ? (
          <>
            {' '}—{' '}
            <button
              type="button"
              className="bnf-linklike"
              onClick={onDownload}
              title="Download the file to open it on your computer"
            >
              download the file ⬇
            </button>
          </>
        ) : (
          '.'
        )}
      </div>
    </div>,
  );
}
