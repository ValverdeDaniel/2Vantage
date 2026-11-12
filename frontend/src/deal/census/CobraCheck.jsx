import { useState } from 'react';
import { setChecklistItem } from '../../api/intake';
import { errorText } from '../../lib/errors';
import { formatDate } from '../../lib/format';
import { useToast } from '../../ui/useToast';

/*
 * "Did anybody check for COBRA participants?" (plan.md §5.3.7, §8.10; C25, O.6 #2; the old CobraCheck.jsx at
 * 891f1b3), on the Census tab because that is where the answer lives. It is not a second record: it ticks the
 * marketing checklist's own `cobra` item in `Intake.checklist`, through intake's door, and the checklist reads the
 * same tick (slice 40). Waived is not "unchecked": somebody decided this deal does not need it, so it is said, not
 * nagged. Stephanie: "a lot of times the clients don't remember to give us the cobra participants and the team
 * forgets to ask."
 */
export default function CobraCheck({ dealId, cobra, onChanged }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (!cobra) return null;

  if (cobra.requirement === 'waived') {
    return (
      <div className="bnf-cobra-check bnf-cobra-waived">
        <span className="bb-badge">COBRA</span>
        <span className="bnf-cobra-text">Marked not needed on this deal.</span>
      </div>
    );
  }

  const checked = Boolean(cobra.checked);
  const stamp = [cobra.by_name, cobra.at ? formatDate(cobra.at) : ''].filter(Boolean).join(' · ');
  async function tick(next) {
    setBusy(true);
    try {
      await setChecklistItem(dealId, { item: 'cobra', checked: next });
      await onChanged?.();
    } catch (error) {
      toast.error(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`bnf-cobra-check ${checked ? 'bnf-cobra-done' : ''}`}>
      <label className="bnf-cobra-label">
        <input type="checkbox" checked={checked} disabled={busy} onChange={(event) => tick(event.target.checked)} />
        <span className="bnf-cobra-text">
          {checked
            ? 'COBRA participants are on this census.'
            : 'Check the COBRA administrator for participants and add them here.'}
        </span>
      </label>
      {checked && stamp && (
        <span className="bnf-cobra-stamp" title={cobra.at || ''}>
          {stamp}
        </span>
      )}
      {!checked && (
        <span className="bnf-cobra-hint">They are quoted with the group. Tick it once confirmed — even if there are none.</span>
      )}
    </div>
  );
}
