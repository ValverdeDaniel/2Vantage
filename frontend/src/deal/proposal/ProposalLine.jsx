import { useId, useState } from 'react';
import { errorText } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import { useToast } from '../../ui/useToast';
import { changeText } from '../advisor/display';
import PreviewTable from './PreviewTable';

const ROLE_WORD = { current: 'Current', renewal: 'Renewal', alternate: 'Alternate' };

function planLabel(plan) {
  return `${plan.option_label ? `${plan.option_label} · ` : ''}${plan.carrier} ${plan.name}`;
}

// One recommendable plan: a tick, its name and figures (the old builder's option rows).
function RecOption({ plan, onChange, details = true }) {
  return (
    <label className="bnf-output-check">
      <input type="checkbox" checked={plan.recommended} onChange={(event) => onChange(plan, event.target.checked)} />
      {planLabel(plan)} — {formatMoney(plan.annual) || 'no price'}
      {details && plan.change && <span className="bb-drop-meta"> {changeText(plan.change)}</span>}
      {details && plan.part_of && <span className="bb-drop-meta"> part of {plan.part_of}&apos;s enrollment</span>}
    </label>
  );
}

/**
 * One line of the proposal (plan.md §8.15): plans to present, our recommendation, why, and the preview — one card in
 * the old proposal builder's look (`bnf-bcard`, `bnf-packet-row`, `bnf-build-rec`).
 */
export default function ProposalLine({ line, reasons, save, recommend }) {
  const toast = useToast();
  const titleId = useId();
  const presentId = useId();
  const [reason, setReason] = useState(null);
  const byId = Object.fromEntries(line.available.map((plan) => [plan.id, plan]));
  const presented = line.plan_ids;
  const locked = (plan) => plan.role === 'current' || plan.recommended;
  const currents = line.available.filter((plan) => plan.role === 'current');
  const candidates = line.available.filter((plan) => plan.role !== 'current');
  // Presented alternates are listed in the order they print, so ▲ ▼ visibly move the plan they were pressed on.
  // At either end the arrow is aria-disabled (move() ignores it) rather than disabled, so focus stays on it.
  const shownAlternates = presented.map((id) => byId[id]).filter((plan) => plan?.role === 'alternate');
  const listed = [
    ...line.available.filter((plan) => plan.role !== 'alternate'),
    ...shownAlternates,
    ...line.available.filter((plan) => plan.role === 'alternate' && !presented.includes(plan.id)),
  ];

  async function present(ids) {
    try {
      await save.mutateAsync({ lines: { [line.line]: ids } });
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  function toggle(plan) {
    present(presented.includes(plan.id) ? presented.filter((id) => id !== plan.id) : [...presented, plan.id]);
  }

  function move(planId, direction) {
    const alternates = presented.filter((id) => byId[id]?.role === 'alternate');
    const index = alternates.indexOf(planId);
    const target = index + direction;
    if (target < 0 || target >= alternates.length) return;
    [alternates[index], alternates[target]] = [alternates[target], alternates[index]];
    present([...presented.filter((id) => byId[id]?.role !== 'alternate'), ...alternates]);
  }

  async function setRecommended(plan, value) {
    try {
      await recommend.mutateAsync({ planId: plan.id, recommended: value });
    } catch (error) {
      toast.error(errorText(error));
    }
  }

  const groups = currents.length
    ? currents.map((current) => ({
        current,
        options: candidates.filter((plan) => plan.base_ids.includes(current.id)),
      }))
    : [{ current: null, options: candidates }];
  const added = currents.length ? candidates.filter((plan) => !plan.base_ids.length) : [];

  return (
    <section className="bb-panel bnf-build-panel bnf-bcard" aria-labelledby={titleId}>
      <div className="bnf-bcard-head">
        <h3 id={titleId} className="bb-panel-title">
          {line.label}
        </h3>
      </div>

      <div role="group" aria-labelledby={presentId}>
        <div id={presentId} className="bnf-packet-group">
          Plans to present {line.is_default && <span className="bnf-state-chip bnf-state-new">default</span>}
          {!line.is_default && (
            <span className="bnf-build-selectall">
              <button type="button" onClick={() => present([])}>
                Back to the default selection
              </button>
            </span>
          )}
        </div>
        {listed.map((plan) => {
          const isOn = presented.includes(plan.id);
          const order = shownAlternates.indexOf(plan);
          return (
            <div key={plan.id} className="bnf-packet-row">
              <label className="bnf-output-check">
                <input type="checkbox" checked={isOn} disabled={locked(plan)} onChange={() => toggle(plan)} />
                {planLabel(plan)}
              </label>
              <span className="bnf-packet-hint">
                {ROLE_WORD[plan.role]}
                {locked(plan) && ' · always shown'}
              </span>
              {plan.role === 'alternate' && isOn && (
                <span className="bnf-build-order">
                  <button
                    type="button"
                    className="bnf-build-order-btn"
                    aria-label={`Move ${plan.name} earlier`}
                    aria-disabled={order === 0}
                    onClick={() => move(plan.id, -1)}
                  >
                    ▲
                  </button>
                  <button
                    type="button"
                    className="bnf-build-order-btn"
                    aria-label={`Move ${plan.name} later`}
                    aria-disabled={order === shownAlternates.length - 1}
                    onClick={() => move(plan.id, 1)}
                  >
                    ▼
                  </button>
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="bnf-build-rec">
        <div className="bnf-packet-group">Our recommendation</div>
        {groups.map(({ current, options }) => (
          <div key={current?.id ?? 'new'} className="bnf-build-panel">
            {current && <div className="bnf-present-head">In place of {current.name}</div>}
            {options.length === 0 && <div className="bb-drop-meta">No renewal or alternate yet.</div>}
            {options.map((plan) => (
              <RecOption key={plan.id} plan={plan} onChange={setRecommended} />
            ))}
            {/* The server's coverage (§5.4): a recommended current plan ("Keep this plan", OQ37) answers for itself. */}
            {current && line.recommendation.missing.includes(current.name) && (
              <div className="bnf-pp-rec-status is-open">⚠ Nothing recommended for {current.name}</div>
            )}
          </div>
        ))}
        {added.length > 0 && (
          <div className="bnf-build-panel">
            <div className="bnf-present-head">Added plans</div>
            {added.map((plan) => (
              <RecOption key={plan.id} plan={plan} onChange={setRecommended} details={false} />
            ))}
          </div>
        )}
        <label className="bnf-build-rec-why">
          <span>Why this, in your words</span>
          <textarea
            rows={3}
            maxLength={2000}
            placeholder={`Why you are recommending this for ${line.label}. The client reads it under the recommendation.`}
            value={reason ?? reasons ?? ''}
            onChange={(event) => setReason(event.target.value)}
            onBlur={() => {
              if (reason !== null && reason !== (reasons ?? '')) {
                save.mutateAsync({ reasons: { [line.line]: reason } }).catch((error) => toast.error(errorText(error)));
              }
              setReason(null);
            }}
          />
        </label>
      </div>

      {line.warnings.map((warning) => (
        <div key={warning} className="bnf-tiersource-note bnf-tiersource-none" role="status">
          ⚠ {warning}
        </div>
      ))}
      <div className="bnf-packet-group">Preview</div>
      <PreviewTable preview={line.preview} />
    </section>
  );
}
