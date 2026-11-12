import cx from '../../../ui/cx';
import { FamilyBody, FamilyPills } from './FamilyControls';
import { BUNDLE, CONCESSION, DUPLICATE, HOLIDAY, candidates, familyMeta } from './pricedKinds';

/*
 * Rung 2 of the priced-version editor (plan.md §8.14; F76–F81; the old PricedVersionComposer), docked above the
 * table, never over it: the same pills and inputs as the draft row, with room for which plans it applies to ("Apply
 * to", with All <carrier>, All and None), the bundle's condition and its check-and-balance (whether each quote's
 * rates already include the bundle, F78), and the version's note and name. ✎ on a version opens it here, locked to
 * its kind; saving re-prices it from the carrier's original.
 */

const SUBTITLES = {
  [CONCESSION]:
    'The original quote is never overwritten — this creates priced versions beside it, recorded in the change history under your name.',
  [BUNDLE]:
    'A function of what the client buys — priced across the carrier’s plans, with and without, so the client sees the differentiator.',
  [HOLIDAY]:
    'A credit, not a rate change — the version keeps the carrier’s rates and carries the credit to the proposal.',
  [DUPLICATE]: 'A standalone copy with every value and its rates — the original is not touched.',
};

function BundlingStates({ kit, plans }) {
  const { priced, draft } = kit;
  const pick = (plan, value) =>
    kit.setBundling(plan, value).then(() => {
      if (value === 'included' && draft.planIds.includes(plan.id))
        kit.reselect(draft.planIds.filter((id) => id !== plan.id));
    });
  return (
    <div className="bnf-pv-states">
      <div className="bnf-pv-states-label">{priced.words.bundling_states}</div>
      {plans.map((plan) => (
        <div key={plan.id} className="bnf-pv-staterow">
          <span className="bnf-pv-statename">
            {plan.carrier} · {plan.name}
          </span>
          <select
            className="filter-select"
            aria-label={`Bundling of ${plan.carrier} ${plan.name}`}
            value={plan.bundling || ''}
            onChange={(event) => pick(plan, event.target.value)}
          >
            {priced.bundling.map((state) => (
              <option key={state.key} value={state.key}>
                {state.label}
              </option>
            ))}
          </select>
        </div>
      ))}
    </div>
  );
}

export default function PricedComposer({ kit }) {
  const { draft, priced } = kit;
  const meta = familyMeta(priced, draft.family);
  const editing = Boolean(draft.editId);
  const pool = candidates(kit.plans, draft.family);
  const anchor = kit.byId.get(draft.anchorId);
  const carriers = [...new Set(pool.map((plan) => plan.carrier))];
  const count = draft.planIds.length;
  const multi = !editing && count > 1;
  const creditBlocked = draft.family === HOLIDAY && multi && Boolean(draft.credit);
  const bundle = draft.family === BUNDLE;
  const copy = draft.family === DUPLICATE;
  const toggle = (id) =>
    kit.reselect(draft.planIds.includes(id) ? draft.planIds.filter((other) => other !== id) : [...draft.planIds, id]);
  const pickAll = (carrier) =>
    kit.reselect(
      pool
        .filter((plan) => (!carrier || plan.carrier === carrier) && !(bundle && plan.bundling === 'included'))
        .map((plan) => plan.id),
    );
  let action = `Add ${count > 1 ? `${count} ${meta.label.toLowerCase()} versions` : meta.label.toLowerCase()}`;
  if (editing) action = 'Save changes';
  if (kit.busy) action = 'Applying…';
  return (
    <div className="bnf-pv-composer">
      <div className="bnf-pv-head">
        <span className="bnf-pv-title">{editing ? `Edit the ${meta.label.toLowerCase()}` : 'Price a version'}</span>
        <span className="bnf-pv-sub">
          {editing
            ? 'Saving re-prices this version from the carrier’s original — cells typed on it since are replaced.'
            : SUBTITLES[draft.family]}
        </span>
        <button
          type="button"
          className="bnf-pv-inline-btn bnf-conc-remove"
          title="Close (the draft is discarded)"
          onClick={kit.cancel}
        >
          ✕
        </button>
      </div>
      <FamilyPills
        priced={priced}
        family={draft.family}
        onFamily={kit.setFamily}
        anchorIsCurrent={anchor?.role === 'current'}
        locked={editing}
      />
      <div className="bnf-pv-planpick">
        {editing || copy ? (
          <span className="bnf-pv-picklabel">
            {editing ? 'Priced from' : 'Copy of'}: {anchor ? `${anchor.carrier} · ${anchor.name}` : '—'}
          </span>
        ) : (
          <>
            <span className="bnf-pv-picklabel">Apply to ({count || 'none'}):</span>
            {pool.map((plan) => {
              const blocked = bundle && plan.bundling === 'included';
              const on = draft.planIds.includes(plan.id);
              return (
                <button
                  key={plan.id}
                  type="button"
                  className={cx('bnf-pv-chip', on && 'bnf-pv-chip-on')}
                  aria-pressed={on}
                  disabled={blocked}
                  title={blocked ? priced.words.included : `${plan.carrier} · ${plan.name}`}
                  onClick={() => toggle(plan.id)}
                >
                  {on ? '✓ ' : ''}
                  {plan.carrier} · {plan.name}
                  {plan.role === 'current' ? ' (current)' : ''}
                </button>
              );
            })}
            <span className="bnf-pv-quick">
              {carriers.length > 1 &&
                carriers.map((carrier) => (
                  <button key={carrier} type="button" className="bnf-pv-quickbtn" onClick={() => pickAll(carrier)}>
                    All {carrier}
                  </button>
                ))}
              <button type="button" className="bnf-pv-quickbtn" onClick={() => pickAll(null)}>
                All
              </button>
              <button type="button" className="bnf-pv-quickbtn" onClick={() => kit.reselect([])}>
                None
              </button>
            </span>
          </>
        )}
      </div>
      <div className="bnf-pv-body">
        <FamilyBody kit={kit} />
        {draft.family === CONCESSION && <div className="bnf-conc-verify">{priced.words.verify}</div>}
        {bundle && (
          <>
            <label className="bnf-filter-check">
              <input
                type="checkbox"
                checked={draft.conditional}
                onChange={(event) => kit.patch({ conditional: event.target.checked })}
              />
              {priced.words.conditional}
              <span className="bnf-conc-was">&nbsp;{priced.words.conditional_hint}</span>
            </label>
            {!editing && <BundlingStates kit={kit} plans={pool.filter((plan) => plan.role !== 'current')} />}
          </>
        )}
        {kit.error && (
          <div className="bnf-conc-verify" role="alert">
            ⚠ {kit.error}
          </div>
        )}
        {kit.warning && <div className="bnf-conc-verify">{kit.warning}</div>}
      </div>
      <div className="bnf-pv-footer">
        {!copy && (
          <>
            <label className="bnf-pv-field">
              <span>
                Note <i>(internal — the client never sees it)</i>
              </span>
              <input
                type="text"
                value={draft.note}
                placeholder="per verbal conversation with the carrier rep…"
                onChange={(event) => kit.patch({ note: event.target.value })}
              />
            </label>
            <label className="bnf-pv-field">
              <span>{multi ? 'Version label (optional — added to each plan’s name)' : 'Version name (optional)'}</span>
              <input
                type="text"
                value={draft.name}
                placeholder={multi ? 'e.g. negotiated' : `${anchor?.name || 'Plan'} — ${meta.label.toLowerCase()}`}
                onChange={(event) => kit.patch({ name: event.target.value })}
              />
            </label>
          </>
        )}
        <span className="bnf-pv-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={kit.cancel}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={kit.commit}
            disabled={kit.busy || (!editing && !count) || creditBlocked}
            title={creditBlocked ? priced.words.one_plan_credit : undefined}
          >
            {action}
          </button>
        </span>
      </div>
    </div>
  );
}
