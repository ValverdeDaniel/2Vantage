import { useEffect, useRef, useState } from 'react';

/*
 * An uploaded image (a photographed or screenshotted quote) (plan.md §8.16; E26): zoom 0.05–6×, Fit, and a status
 * line with its size. Same origin, so a plain <img> carries the session; the image is never changed. Locating a value
 * on an image needs OCR in the browser, which waits (E25, slice 65): until then a value opened here is said, not
 * boxed.
 */
export default function ImageViewer({ url, find = {} }) {
  const [natural, setNatural] = useState(null); // {w, h}
  const [failed, setFailed] = useState(false);
  const [zoom, setZoom] = useState(null); // null: fit the panel's width
  const [wrapW, setWrapW] = useState(0);
  const wrapRef = useRef(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver((entries) => {
      const width = Math.round(entries[0]?.contentRect?.width || 0);
      if (width) setWrapW(width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  if (!url) return null;
  if (failed) {
    return (
      <div className="bb-pdf-notfound" data-render="error" role="alert">
        Could not load the image.
      </div>
    );
  }
  const fit = natural && wrapW ? Math.min(2, Math.max(0.1, (wrapW - 26) / natural.w)) : 1;
  const scale = Math.min(6, Math.max(0.05, (zoom ?? 1) * fit));
  const asked = Boolean(find.value || find.snippet);
  return (
    <div
      className="bb-pdf-viewer bnf-image-viewer"
      data-render={natural ? 'ready' : 'loading'}
      data-find={asked ? 'missing' : 'idle'}
    >
      <div className="bb-pdf-toolbar">
        <span className="bb-pdf-pageinfo">Image{natural ? ` · ${natural.w} × ${natural.h}` : ''}</span>
        <button
          type="button"
          className="bb-pdf-btn"
          title="Zoom out"
          onClick={() => setZoom((z) => Math.max(0.1, (z ?? 1) * 0.8))}
        >
          −
        </button>
        <button
          type="button"
          className="bb-pdf-btn"
          title="Zoom in"
          onClick={() => setZoom((z) => Math.min(6, (z ?? 1) * 1.25))}
        >
          ＋
        </button>
        <button
          type="button"
          className="bb-pdf-btn"
          title="Fit the image to the panel width"
          disabled={zoom === null}
          onClick={() => setZoom(null)}
        >
          Fit
        </button>
        {asked && <span className="bb-pdf-ocrnote">Images are not searched yet: look for the value by eye.</span>}
      </div>
      <div className="bb-pdf-canvas-wrap" ref={wrapRef}>
        <div className="bb-pdf-page">
          {!natural && (
            <div className="bb-pdf-loading" role="status">
              Loading image…
            </div>
          )}
          <img
            src={url}
            alt="The uploaded document"
            className="bnf-image-doc"
            style={natural ? { width: `${Math.round(natural.w * scale)}px` } : undefined}
            onLoad={(event) => {
              const { naturalWidth: w, naturalHeight: h } = event.currentTarget;
              setNatural({ w, h });
            }}
            onError={() => setFailed(true)}
          />
        </div>
      </div>
    </div>
  );
}
