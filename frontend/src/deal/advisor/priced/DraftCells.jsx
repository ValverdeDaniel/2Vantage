import { formatMoney } from '../../../lib/format';
import { DerivedValue, FieldValue } from '../board/cells';
import DraftRowEditor from './DraftRowEditor';
import FormulaControl from './FormulaControl';
import { BUNDLE, CONCESSION, DUPLICATE, HOLIDAY, familyMeta, inheritLabel } from './pricedKinds';
import { formulaLabel } from './stack';

/*
 * The cells of the "Excel stack" under a plan a draft prices (plan.md §8.14; F76; the old AdvisorTab's draft rows):
 * the source plan goes pink, a blue row says HOW the price changes (a dropdown per rate for a concession, the
 * bundle's discount, the holiday's credit) and the violet draft shows the result — red and blue makes purple. Every
 * value and figure in the draft is the server's dry run (`kit.rowFor`); the blue row only echoes what was typed.
 */

function draftLabel(kit, plan) {
  if (plan.derived?.label) return plan.derived.label;
  return kit.draft.family === DUPLICATE ? 'copy' : familyMeta(kit.priced, kit.draft.family).label.toLowerCase();
}

/** The name the version will take: the server's once a dry run answers, else what the person typed or the default. */
function shownName(kit, plan) {
  const { draft } = kit;
  if (plan.derived) return plan.name;
  const typed = draft.name.trim();
  if (draft.family === DUPLICATE) return typed || `${plan.sourceName} — copy`;
  if (typed) return draft.planIds.length > 1 ? `${plan.sourceName} — ${typed}` : typed;
  return `${plan.sourceName} — ${draftLabel(kit, plan)}`;
}

/** The draft's Plan cell: its chip, the credit, carrier and name, and on its anchor the in-row editor. */
export function DraftPlanCell({ plan, kit }) {
  const { draft } = kit;
  const anchor = !draft.expanded && draft.anchorId === plan.sourceId;
  const glyph = familyMeta(kit.priced, draft.family).glyph;
  return (
    <>
      <span className="bnf-plan-chip bnf-chip-draft">
        {glyph} {draft.editId ? 'EDIT' : 'DRAFT'} · {draftLabel(kit, plan)}
        {kit.pending ? ' …' : ''}
      </span>
      {plan.credit?.annual != null && (
        <span className="bnf-pv-credit">− {formatMoney(plan.credit.annual)} credit / yr</span>
      )}
      <div className="bnf-plan-carrier">{plan.carrier}</div>
      <div className="bnf-plan-name">{shownName(kit, plan)}</div>
      {kit.error && (draft.anchorId === plan.sourceId || draft.expanded) && (
        <em className="bnf-saved-error" role="alert">
          ⚠ {kit.error}
        </em>
      )}
      {anchor && <DraftRowEditor kit={kit} />}
    </>
  );
}

/** A value or figure of the draft, for any column but the pinned ones. */
export function DraftCell({ col, plan, ui }) {
  if (col.kind === 'field') return <FieldValue col={col} plan={plan} />;
  if (col.kind !== 'derived' || col.key === 'flags') return null;
  return <DerivedValue col={col} plan={plan} ui={ui} />;
}

function signed(amount, unit) {
  const number = Number(amount);
  if (!number) return '';
  const text = unit === '%' ? `${Math.abs(number)}%` : formatMoney(Math.abs(number));
  return `${number > 0 ? '−' : '+'}${text}`;
}

/** The blue row's cell of a column: a rate's change, the bundle's discount, or the holiday's credit. */
export function FormulaCell({ col, kit }) {
  const { draft, priced } = kit;
  if (col.kind === 'plan') return <span className="bnf-pv-formula-label">{formulaLabel(kit)}</span>;
  if (col.kind === 'field') {
    if (!kit.premiumKeys.includes(col.key)) return null;
    if (draft.family === CONCESSION) {
      return (
        <FormulaControl
          item={draft.each[col.key]}
          inherit={inheritLabel(draft, col.key, priced)}
          ops={priced.ops}
          keep={priced.keep}
          onChange={(next) => kit.setEach(col.key, next)}
        />
      );
    }
    if (draft.family !== BUNDLE) return null;
    const derived = kit.preview(draft.anchorId)?.derived;
    const text = derived ? [signed(derived.pct, '%'), col.key === priced.quoted ? '' : signed(derived.flat, '$')] : [];
    return <span className="bnf-pv-formula-static">{text.filter(Boolean).join(' ') || 'enter the lines'}</span>;
  }
  if (col.key === 'total' && draft.family === HOLIDAY) {
    let text = 'enter the credit';
    if (draft.credit) text = `− ${formatMoney(draft.credit)} / yr credit`;
    else if (draft.months) text = `− ${draft.months} mo credit`;
    return <span className="bnf-pv-formula-static">{text}</span>;
  }
  if (col.key === 'total' || col.key === 'delta') return <span className="bnf-pv-formula-na">auto</span>;
  return null;
}
