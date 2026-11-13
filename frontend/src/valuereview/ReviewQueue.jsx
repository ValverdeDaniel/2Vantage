import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import QueueItem from './QueueItem';
import QueueKeys from './QueueKeys';
import { DEFAULT_KEY_LABELS, movedFrom, nextOpen, progress } from './queueModel';

/*
 * The keyboard review queue (plan.md §8.8; L15; old 891f1b3 `reviewrequest/ReviewQueue.jsx`, D-140, D-142). One item
 * open at a time; A approves, X sends back (or corrects), R leaves it for later, J/K or the arrows move, "?" lists every
 * key, and after a decision the next open item is focused. Props only: the host hands it items and a config per item,
 * does every write in `onDecide`, and forwards its keys through the ref (`act`), since the key listener is the host's
 * (`useReviewHotkeys` with `QUEUE_KEYS`). `decided` is the host's record of what it did this visit; "later" is the
 * queue's own, for this visit only (nothing is stored).
 *
 * onDecide(item, {action, value?, note?}) -> Promise<boolean> (false keeps the item open).
 * renderSummary(item) -> {title, sub?, badge?, icon?, flag?}; renderDetail(item) -> node.
 * cfgFor(item) -> {approve, reject, rejectMode 'value' | 'note', rejectBlocked, needsValue, valueLabel, valuePh,
 *   valueInit, blankAllowed, noteLabel, notePh, noteRequired, noteAction, extras: [{action, label, key, title?,
 *   mode?: 'value', valueLabel, valueInit, blankAllowed}]}. `noteAction` (slice 56) is N's button: a team note on the
 *   item, which leaves it where it is (onDecide(item, {action: 'note', note})); a decision moves on.
 */
const ReviewQueue = forwardRef(function ReviewQueue(
  {
    title,
    items,
    focusId,
    onFocus,
    renderSummary,
    renderDetail,
    cfgFor,
    onDecide,
    decided = {},
    busyId = null,
    header = null,
    emptyNote = 'Nothing to review here.',
    doneNote = '',
    readOnly = false,
    keyLabels = DEFAULT_KEY_LABELS,
  },
  ref,
) {
  const [skipped, setSkipped] = useState(() => new Set());
  const [mode, setMode] = useState(null); // {kind: 'value' | 'note', action, label, placeholder, ...}
  const [draft, setDraft] = useState('');
  const [notice, setNotice] = useState('');
  const [allKeys, setAllKeys] = useState(false);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const item = items.find((entry) => entry.id === focusId) || null;
  const cfg = item ? cfgFor(item) || {} : {};
  const { done, later, pct } = progress(items, decided, skipped);

  useEffect(() => {
    setMode(null);
    setDraft('');
    setNotice('');
    listRef.current?.querySelector(`[data-qid="${String(focusId)}"]`)?.scrollIntoView?.({ block: 'nearest' });
  }, [focusId]);

  const focusInput = () => setTimeout(() => inputRef.current?.focus(), 0);

  async function commit(action, extra = {}) {
    if (!item || busyId != null) return;
    const ok = await onDecide(item, { action, ...extra });
    if (ok === false) return;
    setMode(null);
    setDraft('');
    if (action === 'note') return; // a note leaves the item where it is
    const next = nextOpen(items, item.id, { ...decided, [item.id]: true }, skipped);
    if (next != null) onFocus(next);
  }

  function open(next) {
    setMode(next);
    setDraft(next.init || '');
    focusInput();
  }

  function submit() {
    if (!mode) return undefined;
    const text = draft.trim();
    if (mode.kind === 'value') {
      if (!text && !mode.blankAllowed) return focusInput();
      return commit(mode.action, { value: text });
    }
    if (mode.required && !text) return focusInput();
    return commit(mode.action, { note: text });
  }

  function valueMode(action, from) {
    if (mode?.action === action) return submit();
    return open({
      kind: 'value',
      action,
      label: from.valueLabel,
      placeholder: from.valuePh,
      init: from.valueInit,
      blankAllowed: from.blankAllowed,
    });
  }

  function act(action) {
    if (action === 'help') return setAllKeys((now) => !now);
    if (action === 'next' || action === 'prev') {
      const next = movedFrom(items, focusId, action === 'next' ? 1 : -1);
      return next != null ? onFocus(next) : undefined;
    }
    if (!item || readOnly) return undefined;
    if (action === 'later') {
      const skip = new Set(skipped).add(item.id);
      setSkipped(skip);
      const next = nextOpen(items, item.id, decided, skip);
      return next != null ? onFocus(next) : undefined;
    }
    if (action === 'approve') {
      if (!cfg.approve) return undefined;
      return cfg.needsValue ? valueMode('approve', cfg) : commit('approve');
    }
    if (action === 'note') {
      if (!cfg.noteAction) return undefined;
      if (mode?.action === 'note') return submit();
      return open({ kind: 'note', action: 'note', label: 'Team note', placeholder: 'Only your team sees a team note…', required: true });
    }
    if (action === 'reject') {
      if (!cfg.reject) return undefined;
      if (cfg.rejectBlocked) return setNotice(cfg.rejectBlocked);
      if (cfg.rejectMode === 'value') return valueMode('reject', cfg);
      if (mode?.action === 'reject') return submit();
      return open({
        kind: 'note',
        action: 'reject',
        label: cfg.noteLabel,
        placeholder: cfg.notePh,
        required: Boolean(cfg.noteRequired),
      });
    }
    const extra = (cfg.extras || []).find((entry) => entry.action === action);
    if (!extra) return undefined;
    return extra.mode === 'value' ? valueMode(action, extra) : commit(action);
  }

  useImperativeHandle(ref, () => ({ act }));

  return (
    <div className="rr-queue">
      <div className="rr-queue-head">
        <div className="rr-queue-title">
          <b>{title}</b>
          <span>
            {done} of {items.length} reviewed{later ? ` · ${later} for later` : ''}
          </span>
        </div>
        <div className="rr-queue-prog">
          <i style={{ width: `${pct}%` }} />
        </div>
        {header}
      </div>
      <div className="rr-queue-list" ref={listRef}>
        {!items.length && <div className="rr-queue-empty">{emptyNote}</div>}
        {items.length > 0 && done === items.length && (
          <div className="rr-queue-done">
            <b>✓ All {items.length} reviewed</b>
            {doneNote && <span>{doneNote}</span>}
          </div>
        )}
        {items.map((entry) => {
          const on = entry.id === focusId;
          return (
            <QueueItem
              key={entry.id}
              ref={on ? inputRef : undefined}
              item={entry}
              on={on}
              summary={renderSummary(entry)}
              decided={decided[entry.id]}
              later={!decided[entry.id] && skipped.has(entry.id)}
              cfg={on ? cfg : {}}
              detail={on ? renderDetail(entry) : null}
              mode={on ? mode : null}
              notice={on ? notice : ''}
              busy={busyId != null}
              readOnly={readOnly}
              onFocus={onFocus}
              onAct={act}
              field={{ draft, onDraft: setDraft, onSubmit: submit, onCancel: () => setMode(null) }}
            />
          );
        })}
      </div>
      <QueueKeys
        item={item}
        cfg={cfg}
        keyLabels={keyLabels}
        readOnly={readOnly}
        open={allKeys}
        onToggle={() => setAllKeys((now) => !now)}
      />
    </div>
  );
});

export default ReviewQueue;
