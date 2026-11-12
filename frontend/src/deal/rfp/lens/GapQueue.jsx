import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { patchMember } from '../../../api/census';
import { invalidateDeal } from '../../../api/deals';
import { errorText } from '../../../lib/errors';
import cx from '../../../ui/cx';
import { useToast } from '../../../ui/useToast';
import useReviewHotkeys from '../../../valuereview/useReviewHotkeys';

const QUEUE_KEYS = { a: 'fill', r: 'later' };

/*
 * The gaps this format still has, one item each (plan.md §8.12; K84; old CensusFormatLens.jsx GapQueue on the old
 * ReviewQueue at 891f1b3, `rr-queue` / `rr-qi-*` markup): a required blank's own cell, or a derived column's blank
 * input. A fills the value in (census's own edit, so it is validated, recorded and can be undone there); R leaves it
 * for later. The person is named here, on our own screen, never in a file. Asking the client (X, "＋ Ask") arrives
 * with the request tray.
 */
export default function GapQueue({ dealId, items, total }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [focus, setFocus] = useState(items[0]?.id ?? null);
  const [values, setValues] = useState({});
  const [decided, setDecided] = useState({});
  const [busy, setBusy] = useState(null);
  const open = items.filter((item) => !decided[item.id]);
  const after = (id) => open.find((item) => item.id !== id)?.id ?? null;
  const pct = items.length ? Math.round((100 * (items.length - open.length)) / items.length) : 100;

  const fill = async (item) => {
    const value = (values[item.id] || '').trim();
    if (!value || busy) return;
    setBusy(item.id);
    try {
      await patchMember(item.member_id, { values: { [item.field]: value } });
      setDecided((now) => ({ ...now, [item.id]: 'filled' }));
      setFocus(after(item.id));
      invalidateDeal(queryClient, dealId);
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not save that value.' }));
    } finally {
      setBusy(null);
    }
  };
  const later = (item) => {
    setDecided((now) => ({ ...now, [item.id]: 'later' }));
    setFocus(after(item.id));
  };
  const focused = items.find((item) => item.id === focus && !decided[item.id]);
  useReviewHotkeys({
    enabled: Boolean(focused),
    keys: QUEUE_KEYS,
    onKey: (action) => (action === 'fill' ? fill(focused) : later(focused)),
  });

  return (
    <div className="rr-queue" data-guide="census-lens-gap-queue">
      <div className="rr-queue-head">
        <div className="rr-queue-title">
          Gaps to fix · {open.length} open
          {total > items.length ? ` (the first ${items.length} of ${total})` : ''}
        </div>
        <div className="rr-queue-prog">
          <i style={{ width: `${pct}%` }} />
        </div>
      </div>
      <div className="rr-queue-list">
        {open.length === 0 && <div className="rr-queue-done">Filled values are on the census.</div>}
        {items.map((item) => {
          const state = decided[item.id];
          const on = item.id === focus && !state;
          return (
            <div
              key={item.id}
              className={cx('rr-qi', on && 'rr-qi-on', state && 'rr-qi-done')}
              onClick={() => !state && setFocus(item.id)}
            >
              <span
                className={cx(
                  'rr-qi-ico',
                  state === 'filled' && 'rr-qi-ico-ok',
                  state === 'later' && 'rr-qi-ico-later',
                )}
              >
                {state === 'filled' ? '✓' : state === 'later' ? '↷' : '•'}
              </span>
              <div className="rr-qi-main">
                <div className="rr-qi-title">
                  {item.person} · {item.header}
                </div>
                {!on && (
                  <div className="rr-qi-sub">
                    {item.derived
                      ? `Needs ${item.field_label}, which it is worked out from`
                      : 'Blank — the carrier requires it'}
                  </div>
                )}
              </div>
              <div className="rr-qi-badge">
                <span className="rr-change-chip rr-change-cleared">
                  {state === 'filled' ? 'Filled in' : state === 'later' ? 'Later' : 'Gap'}
                </span>
              </div>
              {on && (
                <div className="rr-qi-detail">
                  <div className="rr-qi-hint">
                    ⓘ{' '}
                    {item.derived
                      ? `${item.header} is worked out from ${item.field_label}: fill that in.`
                      : `${item.header} is required on this carrier's file and blank for ${item.person}.`}
                  </div>
                  <div className="rr-qi-field">
                    <input
                      className="bnf-intake-input"
                      aria-label={`${item.field_label} for ${item.person}`}
                      placeholder={item.field_label}
                      value={values[item.id] || ''}
                      onChange={(event) => setValues((now) => ({ ...now, [item.id]: event.target.value }))}
                      onKeyDown={(event) => event.key === 'Enter' && fill(item)}
                    />
                  </div>
                  <div className="rr-qi-actions">
                    <button
                      type="button"
                      className="rr-qi-act rr-qi-act-ok"
                      disabled={busy === item.id}
                      onClick={() => fill(item)}
                    >
                      {busy === item.id ? 'Saving…' : 'Fill in'}
                    </button>
                    <button type="button" className="rr-qi-act rr-qi-act-later" onClick={() => later(item)}>
                      Later
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="rr-queue-keys">A fill in · R later</div>
    </div>
  );
}
