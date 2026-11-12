import { useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useModalLayer } from './useModalLayer';

/**
 * The old right-hand drawer (the Work with Claude drawer's .bnf-scan-drawer): fixed under the top bar, with the page
 * beside it still usable. Escape or ✕ closes it and focus returns to what opened it.
 *   open, onClose, title, sub (a grey line at the top of the body), children
 */
export default function Drawer({ open, ...props }) {
  return open ? <DrawerPanel {...props} /> : null;
}

function DrawerPanel({ onClose, title, sub, children }) {
  const ref = useRef(null);
  const titleId = useId();
  useModalLayer(ref, { focusField: false, onEscape: onClose, modal: false });

  return createPortal(
    <aside ref={ref} className="bnf-scan-drawer" role="dialog" aria-labelledby={titleId}>
      <div className="bnf-scan-drawer-head">
        <span id={titleId} className="bnf-scan-drawer-title">
          {title}
        </span>
        <button type="button" className="bnf-scan-drawer-close" aria-label={`Close ${title}`} onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="bnf-scan-drawer-body" data-dialog-body>
        {sub && <div className="bnf-scan-drawer-sub">{sub}</div>}
        {children}
      </div>
    </aside>,
    document.body,
  );
}
