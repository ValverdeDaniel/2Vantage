import { useEffect, useRef, useState } from 'react';
import Highlights from './Highlights';
import useImageFind from './useImageFind';

/*
 * An uploaded image (a photographed or screenshotted quote) (plan.md §8.16; E25, E26): zoom 0.05–6×, Fit, and a status
 * line with its size. Same origin, so a plain <img> carries the session; the image is never changed. A value opened
 * here is found by browser OCR, read once per image (useImageFind), and boxed; OCR only draws (data-find `ocr`).
 */
export default function ImageViewer({ url, find = {}, jumpKey = 0 }) {
  const [natural, setNatural] = useState(null); // {w, h}
  const [failed, setFailed] = useState(false);
  const [zoom, setZoom] = useState(null); // null: fit the panel's width
  const [wrapW, setWrapW] = useState(0);
  const wrapRef = useRef(null);
  const imgRef = useRef(null);

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

  const fit = natural && wrapW ? Math.min(2, Math.max(0.1, (wrapW - 26) / natural.w)) : 1;
  const scale = Math.min(6, Math.max(0.05, (zoom ?? 1) * fit));
  const located = useImageFind({ img: imgRef, url, natural, scale, find, jumpKey });

  if (!url) return null;
  if (failed) {
    return (
      <div className="bb-pdf-notfound" data-render="error" role="alert">
        Could not load the image.
      </div>
    );
  }
  return (
    <div
      className="bb-pdf-viewer bnf-image-viewer"
      data-render={natural ? 'ready' : 'loading'}
      data-find={located.state}
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
        {located.state === 'reading' && (
          <span className="bb-pdf-ocrnote">⏳ Locating on the image… (the first time can take ~15s)</span>
        )}
        {located.state === 'ocr' && <span className="bb-pdf-foundnote">✓ Located on the image</span>}
        {located.state === 'missing' && (
          <span className="bb-pdf-notfound-inline">⚠ Couldn&apos;t locate the exact text on this image.</span>
        )}
      </div>
      <div className="bb-pdf-canvas-wrap" ref={wrapRef}>
        <div className="bb-pdf-page">
          {!natural && (
            <div className="bb-pdf-loading" role="status">
              Loading image…
            </div>
          )}
          <img
            ref={imgRef}
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
          <Highlights boxes={located.boxes} flashKey={`${jumpKey}-image`} />
        </div>
      </div>
    </div>
  );
}
