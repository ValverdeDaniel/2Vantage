import { forwardRef } from 'react';
import QueueField from './QueueField';
import { Kbd } from './QueueKeys';
import { approveWords, rejectWords } from './queueModel';

/*
 * One row of the review queue (L15; old 891f1b3 `ReviewQueue.jsx` `rr-qi`): its mark (decided, later, or the item's
 * own icon), title and badge; the focused row opens its detail, what was decided, the box a value or note goes in, a
 * notice (why X cannot act), and its buttons with their keys.
 */
const QueueItem = forwardRef(function QueueItem(
  { item, on, summary, decided, later, cfg, detail, mode, notice, busy, readOnly, onFocus, onAct, field },
  inputRef,
) {
  const mark = decided ? decided.icon || '✓' : later ? '◷' : summary.icon || '';
  const iconClass = `rr-qi-ico${decided ? ` rr-qi-ico-${decided.tone || 'ok'}` : ''}${later ? ' rr-qi-ico-later' : ''}`;
  return (
    <div
      data-qid={String(item.id)}
      className={`rr-qi${on ? ' rr-qi-on' : ''}${decided && !on ? ' rr-qi-done' : ''}`}
      onClick={() => !on && onFocus(item.id)}
    >
      <span className={iconClass}>{mark}</span>
      <div className="rr-qi-main">
        <div className="rr-qi-title">{summary.title}</div>
        {!on && summary.sub && <div className="rr-qi-sub">{summary.sub}</div>}
      </div>
      <div className="rr-qi-badge">
        {summary.badge}
        {summary.flag && <span className="rr-flag-chip">{summary.flag}</span>}
      </div>
      {on && (
        <div className="rr-qi-detail">
          {detail}
          {decided && (
            <div className={`rr-qi-decided rr-qi-decided-${decided.tone || 'ok'}`}>
              <b>{decided.label}</b>
              {decided.value ? ` · ${decided.value}` : ''}
              {decided.after}
            </div>
          )}
          {mode && <QueueField ref={inputRef} mode={mode} {...field} />}
          {notice && !mode && (
            <div className="rr-hint rr-qi-notice" role="status">
              <span>ⓘ</span>
              {notice}
            </div>
          )}
          {!readOnly && (
            <div className="rr-qi-actions">
              {cfg.approve && (
                <button
                  type="button"
                  className="rr-qi-act rr-qi-act-ok"
                  title={approveWords(cfg)}
                  disabled={busy}
                  onClick={() => onAct('approve')}
                >
                  {cfg.approve}
                  <Kbd k="A" />
                </button>
              )}
              {cfg.reject && (
                <button
                  type="button"
                  className={`rr-qi-act${mode?.action === 'reject' ? ' rr-qi-act-on' : ''}`}
                  disabled={busy || Boolean(cfg.rejectBlocked)}
                  title={rejectWords(cfg)}
                  onClick={() => onAct('reject')}
                >
                  {cfg.reject}
                  <Kbd k="X" />
                </button>
              )}
              {(cfg.extras || []).map((extra) => (
                <button
                  key={extra.action}
                  type="button"
                  className={`rr-qi-act${mode?.action === extra.action ? ' rr-qi-act-on' : ''}`}
                  title={`${extra.label}${extra.key ? ` (${extra.key})` : ''}${extra.title ? `: ${extra.title}` : ''}`}
                  disabled={busy}
                  onClick={() => onAct(extra.action)}
                >
                  {extra.label}
                  {extra.key && <Kbd k={extra.key} />}
                </button>
              ))}
              {cfg.noteAction && (
                <button
                  type="button"
                  className={`rr-qi-act${mode?.action === 'note' ? ' rr-qi-act-on' : ''}`}
                  disabled={busy}
                  title="A note on it for your team (N): the client never sees it, and the item stays where it is"
                  onClick={() => onAct('note')}
                >
                  {cfg.noteAction}
                  <Kbd k="N" />
                </button>
              )}
              <button
                type="button"
                className="rr-qi-act rr-qi-act-later"
                title="Later (R): leave it for now and move on, for this visit only: nothing is saved"
                onClick={() => onAct('later')}
              >
                Later
                <Kbd k="R" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
});

export default QueueItem;
