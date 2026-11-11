import { useState } from 'react';
import { errorText } from '../../lib/errors';
import { formatMoney } from '../../lib/format';
import Button from '../../ui/Button';
import IconButton from '../../ui/IconButton';
import TextInput from '../../ui/TextInput';
import { useToast } from '../../ui/useToast';
import { changeText } from '../advisor/display';
import PreviewTable from './PreviewTable';
import styles from './ProposalTab.module.css';

const ROLE_WORD = { current: 'Current', renewal: 'Renewal', alternate: 'Alternate' };

function planLabel(plan) {
  return `${plan.option_label ? `${plan.option_label} · ` : ''}${plan.carrier} ${plan.name}`;
}

/** One line of the proposal (plan.md §8.12): plans to present, our recommendation, why, and the preview. */
export default function ProposalLine({ line, reasons, save, recommend }) {
  const toast = useToast();
  const [reason, setReason] = useState(null);
  const byId = Object.fromEntries(line.available.map((plan) => [plan.id, plan]));
  const presented = line.plan_ids;
  const locked = (plan) => plan.role === 'current' || plan.recommended;
  const currents = line.available.filter((plan) => plan.role === 'current');
  const candidates = line.available.filter((plan) => plan.role !== 'current');
  // Presented alternates are listed in the order they print, so ↑ ↓ visibly move the plan they were pressed on.
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
    <section className={styles.line} aria-labelledby={`line-${line.line}`}>
      <h3 id={`line-${line.line}`}>{line.label}</h3>
      <div className={styles.columns}>
        <fieldset className={styles.block}>
          <legend>Plans to present {line.is_default && <span className={styles.muted}>(default)</span>}</legend>
          {listed.map((plan) => {
            const isOn = presented.includes(plan.id);
            const isAlternate = plan.role === 'alternate' && isOn;
            const order = shownAlternates.indexOf(plan);
            return (
              <div key={plan.id} className={styles.planRow}>
                <label>
                  <input type="checkbox" checked={isOn} disabled={locked(plan)} onChange={() => toggle(plan)} />{' '}
                  {planLabel(plan)} <span className={styles.muted}>{ROLE_WORD[plan.role]}</span>
                  {locked(plan) && <span className={styles.muted}> · always shown</span>}
                </label>
                {isAlternate && (
                  <span className={styles.moves}>
                    <IconButton
                      label={`Move ${plan.name} earlier`}
                      size="sm"
                      aria-disabled={order === 0}
                      onClick={() => move(plan.id, -1)}
                    >
                      ↑
                    </IconButton>
                    <IconButton
                      label={`Move ${plan.name} later`}
                      size="sm"
                      aria-disabled={order === shownAlternates.length - 1}
                      onClick={() => move(plan.id, 1)}
                    >
                      ↓
                    </IconButton>
                  </span>
                )}
              </div>
            );
          })}
          {!line.is_default && (
            <Button size="sm" variant="ghost" onClick={() => present([])}>
              Back to the default selection
            </Button>
          )}
        </fieldset>

        <fieldset className={styles.block}>
          <legend>Our recommendation</legend>
          {groups.map(({ current, options }) => (
            <div key={current?.id ?? 'new'} className={styles.recGroup}>
              {current && <p className={styles.recCurrent}>In place of {current.name}</p>}
              {options.length === 0 && <p className={styles.muted}>No renewal or alternate yet.</p>}
              {options.map((plan) => (
                <label key={plan.id} className={styles.recOption}>
                  <input
                    type="checkbox"
                    checked={plan.recommended}
                    onChange={(event) => setRecommended(plan, event.target.checked)}
                  />{' '}
                  {planLabel(plan)} — {formatMoney(plan.annual) || 'no price'}
                  {plan.change && <span className={styles.muted}> {changeText(plan.change)}</span>}
                  {plan.part_of && <span className={styles.muted}> part of {plan.part_of}&apos;s enrollment</span>}
                </label>
              ))}
              {current && !options.some((plan) => plan.recommended) && (
                <p className={styles.blocker}>
                  <span aria-hidden="true">⚠ </span>Nothing recommended for {current.name}
                </p>
              )}
            </div>
          ))}
          {added.length > 0 && (
            <div className={styles.recGroup}>
              <p className={styles.recCurrent}>Added plans</p>
              {added.map((plan) => (
                <label key={plan.id} className={styles.recOption}>
                  <input
                    type="checkbox"
                    checked={plan.recommended}
                    onChange={(event) => setRecommended(plan, event.target.checked)}
                  />{' '}
                  {planLabel(plan)} — {formatMoney(plan.annual) || 'no price'}
                </label>
              ))}
            </div>
          )}
          <label className={styles.reasonLabel} htmlFor={`reason-${line.line}`}>
            Why we recommend it
          </label>
          <TextInput
            id={`reason-${line.line}`}
            multiline
            rows={3}
            maxLength={2000}
            value={reason ?? reasons ?? ''}
            onChange={(event) => setReason(event.target.value)}
            onBlur={() => {
              if (reason !== null && reason !== (reasons ?? '')) {
                save.mutateAsync({ reasons: { [line.line]: reason } }).catch((error) => toast.error(errorText(error)));
              }
              setReason(null);
            }}
          />
        </fieldset>
      </div>
      {line.warnings.map((warning) => (
        <p key={warning} className={styles.warning} role="status">
          <span aria-hidden="true">⚠ </span>
          {warning}
        </p>
      ))}
      <h4 className={styles.previewTitle}>Preview</h4>
      <PreviewTable preview={line.preview} />
    </section>
  );
}
