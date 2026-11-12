import { formatMoney } from '../../../lib/format';
import cx from '../../../ui/cx';
import BundleControls from './BundleControls';
import FormulaControl from './FormulaControl';
import { familyAllowed, inheritLabel } from './pricedKinds';

/*
 * The controls of the priced-version draft (plan.md §8.14; F76–F81; the old PricedVersionComposer): the family pills
 * — the same row in the draft row and in the docked composer — and each family's inputs. A concession is one change
 * on all rates, then each rate on its own; a premium holiday a dollar credit a year or free months; a duplicate only
 * its name; the bundling discount is BundleControls. `FamilyBody` picks the draft's. Words and operations come from meta
 * (board.priced); the figures a family shows ("≈ $1,520 on Cigna") come from the server's dry run.
 */

export function FamilyPills({ priced, family, onFamily, anchorIsCurrent, locked, compact }) {
  return (
    <div className={cx('bnf-pv-family', compact && 'bnf-pv-family-compact')} role="tablist">
      {priced.families.map((f) => {
        const blocked = anchorIsCurrent && !familyAllowed(f.key, { role: 'current' });
        const disabled = locked ? f.key !== family : blocked;
        let title = f.hint;
        if (locked && f.key !== family) {
          title = 'An existing version keeps its kind — remove it and add a new one to change what it is';
        } else if (blocked) {
          title = priced.words.current_plan;
        }
        return (
          <button
            key={f.key}
            type="button"
            role="tab"
            aria-selected={family === f.key}
            className={cx('bnf-pv-family-pill', family === f.key && 'bnf-pv-family-on')}
            disabled={disabled}
            title={title}
            onClick={() => onFamily(f.key)}
          >
            <span className="bnf-pv-glyph">{f.glyph}</span>
            {compact ? f.short : f.label}
          </button>
        );
      })}
    </div>
  );
}

export function ConcessionControls({ priced, draft, onDraft, rateKeys, labelOf, compact, onKeyDown }) {
  const setOverride = (key, next) => {
    const each = { ...draft.each };
    if (next == null) delete each[key];
    else each[key] = next;
    onDraft({ each });
  };
  const overrides = Object.keys(draft.each).filter((key) => rateKeys.includes(key));
  const showEach = (!compact || draft.eachOpen) && rateKeys.length > 1;
  return (
    <div className="bnf-pv-conc">
      <div className="bnf-pv-allrow">
        <select
          className="bnf-pv-formula-op"
          aria-label="Change on all rates"
          value={draft.allOp}
          onChange={(event) => onDraft({ allOp: event.target.value })}
          onKeyDown={onKeyDown}
        >
          {priced.ops.map((op) => (
            <option key={op.key} value={op.key}>
              {op.label}
            </option>
          ))}
        </select>
        <input
          type="number"
          className="bnf-filter-num"
          aria-label="Amount on all rates"
          min="0"
          step="0.25"
          value={draft.allValue}
          placeholder={priced.pct_ops.includes(draft.allOp) ? '%' : '$'}
          onChange={(event) => onDraft({ allValue: event.target.value })}
          onKeyDown={onKeyDown}
          autoFocus
        />
        <span className="bnf-pv-inline-label">{rateKeys.length > 1 ? `all ${rateKeys.length} rates` : 'the rate'}</span>
        {compact && rateKeys.length > 1 && (
          <button
            type="button"
            className="bnf-pv-quickbtn"
            title="Change one rate on its own — or leave one out of the all-rates change"
            onClick={() => onDraft({ eachOpen: !draft.eachOpen })}
          >
            Each rate {draft.eachOpen ? '▾' : '▸'}
            {!draft.eachOpen && overrides.length ? ` (${overrides.length})` : ''}
          </button>
        )}
      </div>
      {showEach && (
        <div className="bnf-pv-eachlist">
          {rateKeys.map((key) => (
            <label key={key} className="bnf-pv-eachrow">
              <span className="bnf-pv-eachname">{labelOf(key)}</span>
              <FormulaControl
                item={draft.each[key]}
                inherit={inheritLabel(draft, key, priced)}
                ops={priced.ops}
                keep={priced.keep}
                onChange={(next) => setOverride(key, next)}
              />
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

export function HolidayControls({ priced, draft, onDraft, compact, multi, credit, carrier, onKeyDown }) {
  return (
    <div className="bnf-pv-holiday">
      {!compact && <div className="bb-modal-sub">{priced.words.holiday}</div>}
      <div className="bnf-pv-allrow">
        <label className="bnf-filter-num-wrap">
          $&nbsp;
          <input
            type="number"
            className="bnf-filter-num"
            value={draft.credit}
            min="0"
            placeholder="credit"
            onChange={(event) => onDraft({ credit: event.target.value })}
            onKeyDown={onKeyDown}
            autoFocus
          />
          &nbsp;credit / yr
        </label>
        <span className="bnf-conc-or">or</span>
        <label className="bnf-filter-num-wrap">
          <input
            type="number"
            className="bnf-filter-num"
            value={draft.months}
            min="1"
            max="12"
            placeholder="#"
            onChange={(event) => onDraft({ months: event.target.value })}
            onKeyDown={onKeyDown}
          />
          &nbsp;free month{Number(draft.months) === 1 ? '' : 's'}
        </label>
        {draft.months && !draft.credit && credit?.annual != null && !multi ? (
          <span className="bnf-conc-was">
            ≈ {formatMoney(credit.annual)}
            {carrier ? ` on ${carrier}` : ''}
          </span>
        ) : null}
      </div>
      {multi && draft.credit ? <div className="bnf-conc-verify">{priced.words.one_plan_credit}</div> : null}
    </div>
  );
}

export function DuplicateControls({ draft, onDraft, anchor, compact, onKeyDown }) {
  return (
    <div className="bnf-pv-duplicate">
      <label className="bnf-conc-field">
        Name this copy:&nbsp;
        <input
          type="text"
          className="bnf-input"
          value={draft.name}
          placeholder={anchor ? `${anchor.name} — copy` : 'Copy'}
          onChange={(event) => onDraft({ name: event.target.value })}
          onKeyDown={onKeyDown}
        />
      </label>
      {!compact && (
        <div className="bnf-conc-verify">
          A separate plan column, copied from <b>{anchor ? `${anchor.carrier} · ${anchor.name}` : 'this plan'}</b>, with
          its rates — the original is not touched. Use it when a carrier reissues the same plan name with a different
          design, or when the reader mis-read a second quote; change its rows in the table once it is added.
        </div>
      )}
    </div>
  );
}

/** The inputs of the draft's family, in the draft row (`compact`) or the docked composer. */
export function FamilyBody({ kit, compact, onKeyDown }) {
  const { draft, priced } = kit;
  const anchor = kit.byId.get(draft.anchorId);
  const shared = { priced, draft, onDraft: kit.patch, compact, onKeyDown };
  if (draft.family === 'concession') {
    return <ConcessionControls {...shared} rateKeys={kit.rateKeys} labelOf={kit.labelOf} />;
  }
  if (draft.family === 'bundle') {
    return (
      <BundleControls
        {...shared}
        anchor={anchor}
        index={kit.index}
        lineLabel={kit.lineLabel}
        preview={kit.preview(draft.anchorId)}
        scope={draft.planIds.length}
      />
    );
  }
  if (draft.family === 'holiday') {
    const multi = !draft.editId && draft.planIds.length > 1;
    const credit = kit.preview(draft.anchorId)?.credit;
    return <HolidayControls {...shared} multi={multi} credit={credit} carrier={anchor?.carrier} />;
  }
  return <DuplicateControls {...shared} anchor={anchor} />;
}
