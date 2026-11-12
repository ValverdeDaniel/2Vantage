import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { stopActiveDictation } from '../../voice/localSpeech';

/*
 * The Work with Claude drawer (plan.md §8.17; D4; the old ScanDrawer): a right panel over the page, with no scrim, so
 * the table behind stays usable; min(560 px, 94 vw), widening to 880 px while a review card shows (the stylesheet's
 * `:has(.bnf-staged-review)`). Not the modal kit drawer (`ui/Drawer`). Escape closes it, unless a dialog is open
 * over it (the dialog takes its own Escape); while the mic is dictating, Escape stops the mic first (D4, D20).
 * `headerExtra` sits in the head (the "Reading" picker, D5).
 */
export default function ClaudeDrawer({ title = 'Work with Claude', headerExtra = null, onClose, children }) {
  useEffect(() => {
    const onKey = (event) => {
      if (event.key !== 'Escape' || document.querySelector('[aria-modal="true"]')) return;
      if (!stopActiveDictation()) onClose?.();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return createPortal(
    <div className="bnf-scan-drawer" role="dialog" aria-label={title}>
      <div className="bnf-scan-drawer-head">
        <div className="bnf-scan-drawer-title">{title}</div>
        {headerExtra}
        <button type="button" className="bnf-scan-drawer-close" onClick={onClose} title="Close (Esc)" aria-label="Close">
          ✕
        </button>
      </div>
      <div className="bnf-scan-drawer-body">{children}</div>
    </div>,
    document.body,
  );
}

/** The head's "Reading" picker (D5): what the files attached here are filed as and read as, for everyone. `labels`
 *  names a kind otherwise (the Questionnaire tab: each form's own name, G102). */
export function ReadingPicker({ kinds, kind, meta, labels = {}, onKind, disabled = false }) {
  if (kinds.length < 2) return null;
  return (
    <label className="bnf-wwc-kinds" title="What the files you attach here are">
      Reading
      <select value={kind} disabled={disabled} onChange={(event) => onKind(event.target.value)}>
        {kinds.map((key) => (
          <option key={key} value={key}>
            {labels[key] || meta.document_kinds.find((entry) => entry.key === key)?.label || key}
          </option>
        ))}
      </select>
    </label>
  );
}
