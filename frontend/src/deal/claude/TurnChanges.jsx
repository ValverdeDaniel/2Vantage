import { useState } from 'react';
import { useApplyTurn, useDiscardTurn, useUndoTurn } from '../../api/chats';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import { changesState, changesTitle } from './chatWords';
import { flashWhenSettled } from './flashPlans';
import { useQueryClient } from '@tanstack/react-query';

/*
 * What a chat turn proposed for the deal, under Claude's reply (plan.md §10.6; D31, D71, D73, D85, D86; the old
 * ProposedChangesCard, `bnf-pchg-*`): each change with its tick — the plan, and each value old → new — and Claude's
 * checks. Changes that wait (a producer's, or a locked table's) are applied with "Apply N selected ▸" or dropped with
 * Discard; changes that landed by themselves, or once applied, offer ↶ Undo this run.
 */
function Values({ item }) {
  if (!item.values) return item.reason ? <div className="bnf-pchg-meta">{item.reason}</div> : null;
  return (
    <>
      {item.values.map((value) => (
        <div key={value.key} className="bnf-pchg-row">
          <span className="bnf-pchg-field">{value.label}</span>
          <span className="bnf-pchg-values">
            <span className="bnf-pchg-old">{value.old || '—'}</span>
            {' → '}
            <span className="bnf-pchg-new">{value.new || '—'}</span>
          </span>
          <span className="bnf-pchg-meta">{value.dictated ? 'as you said' : ''}</span>
        </div>
      ))}
    </>
  );
}

export default function TurnChanges({ dealId, chatId, turn }) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const apply = useApplyTurn(dealId, chatId);
  const undo = useUndoTurn(dealId, chatId);
  const discard = useDiscardTurn(dealId, chatId);
  const items = turn.items || [];
  const [picked, setPicked] = useState(() => new Set(items.filter((item) => item.tick).map((item) => item.id)));
  const state = changesState(turn);
  if (!state) return null;
  const waiting = state === 'waiting';
  const busy = apply.isPending || undo.isPending || discard.isPending;

  async function run(action, body, said) {
    try {
      const answer = await action.mutateAsync(body);
      const plans = answer?.landed?.plan_ids || [];
      if (plans.length) flashWhenSettled(queryClient, dealId, plans);
      if (said) toast.success(said);
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  const toggle = (id) =>
    setPicked((now) => {
      const next = new Set(now);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <div className={`bnf-pchg${waiting ? '' : ' bnf-pchg-done'}`} data-turn-changes={turn.id}>
      <div className="bnf-pchg-head">
        <div>
          <div className="bnf-pchg-title">{changesTitle(turn)}</div>
          <div className="bnf-pchg-sub">
            {waiting && (turn.wait_reason || 'Nothing has changed yet — untick anything wrong, then apply.')}
            {state === 'applied' && (turn.landed?.summary || turn.summary)}
          </div>
        </div>
      </div>
      <div className="bnf-pchg-list">
        {items.map((item) => (
          <div key={item.id} className="bnf-pchg-plan">
            <label className="bnf-pchg-plan-name">
              {waiting && (
                <input type="checkbox" checked={picked.has(item.id)} disabled={busy} onChange={() => toggle(item.id)} />
              )}{' '}
              {item.label}
            </label>
            <Values item={item} />
          </div>
        ))}
      </div>
      {(turn.findings || []).length > 0 && (
        <div className="bnf-pchg-note">Checks: {turn.findings.map((finding) => finding.text).join('; ')}.</div>
      )}
      <div className="bnf-pchg-actions">
        {waiting && (
          <>
            <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => run(discard, turn.id)}>
              Discard
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy || picked.size === 0}
              onClick={() => run(apply, { jobId: turn.id, select: [...picked] }, 'Applied — ↶ Undo this run takes it back.')}
            >
              {apply.isPending ? 'Applying…' : `Apply ${picked.size} selected ▸`}
            </button>
          </>
        )}
        {state === 'applied' && (
          <button
            type="button"
            className="btn btn-secondary btn-sm bnf-work-undo"
            disabled={busy}
            title="Put the table back the way it was before this run"
            onClick={() => run(undo, { jobId: turn.id }, 'Undone — the table is back the way it was before that run.')}
          >
            {undo.isPending ? 'Undoing…' : '↶ Undo this run'}
          </button>
        )}
      </div>
    </div>
  );
}
