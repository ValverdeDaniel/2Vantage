import { useMemo } from 'react';
import cx from '../../../ui/cx';
import { requirementDetail } from './pricedKinds';

/*
 * The bundling discount (plan.md §8.14; F78; the old BundleControls): per placed line, its own operation (% or $,
 * off or up), its amount, and the quote that has to sell for the discount to be real ("if we sell Aetna dental, we
 * get 5% off the medical"). A line that gets an amount and has exactly one quote from this carrier links to it; blank
 * names the carrier alone (a line nobody has quoted yet). The "=" line — the combined discount and what it requires —
 * is the server's dry run, worded; linking another carrier's quote is allowed but said out loud. Bundle templates
 * (the old cheat sheet, F79) wait.
 */

const same = (a, b) =>
  String(a ?? '')
    .trim()
    .toLowerCase() ===
  String(b ?? '')
    .trim()
    .toLowerCase();

function partOf(draft, line) {
  return { op: 'pct_off', value: '', plan_id: null, ...(draft.parts?.[line] ?? {}) };
}

export default function BundleControls({
  priced,
  draft,
  onDraft,
  compact,
  anchor,
  index,
  lineLabel,
  preview,
  scope,
  onKeyDown,
}) {
  const carrier = anchor?.carrier ?? '';
  const ops = priced.ops.filter((op) => priced.bundle_ops.includes(op.key));
  // Every quote each bundled line could require, this carrier's first; a priced version is not a line's quote.
  const byLine = useMemo(() => {
    const out = {};
    for (const entry of index ?? []) {
      (out[entry.line] ??= []).push(entry);
    }
    for (const list of Object.values(out)) {
      list.sort(
        (a, b) =>
          (same(a.carrier_name, carrier) ? 0 : 1) - (same(b.carrier_name, carrier) ? 0 : 1) ||
          `${a.carrier_name} ${a.name}`.localeCompare(`${b.carrier_name} ${b.name}`),
      );
    }
    return out;
  }, [index, carrier]);
  const setPart = (line, next) => onDraft({ parts: { ...draft.parts, [line]: { ...partOf(draft, line), ...next } } });
  const autoLink = (line, part) => {
    if (part.plan_id) return part.plan_id;
    const mine = (byLine[line] ?? []).filter((entry) => same(entry.carrier_name, carrier));
    return mine.length === 1 ? mine[0].id : null;
  };
  const crossCarrier = Object.entries(draft.parts ?? {})
    .filter(([, part]) => part?.value && part.plan_id)
    .map(([line, part]) => (byLine[line] ?? []).find((entry) => entry.id === part.plan_id))
    .filter((entry) => entry && !same(entry.carrier_name, carrier))
    .map((entry) => `${entry.carrier_name} · ${entry.name}`);
  const requires = requirementDetail(preview?.derived, lineLabel);
  return (
    <div className="bnf-pv-bundle">
      <div className={cx('bnf-pv-bundlegrid', compact && 'bnf-pv-bundlegrid-compact')}>
        {priced.bundle_lines.map(({ key, short }) => {
          const part = partOf(draft, key);
          return (
            <div key={key} className="bnf-pv-bundleline">
              <span className="bnf-pv-bundlename">{compact ? short : lineLabel(key)}</span>
              <select
                className="bnf-pv-formula-op"
                aria-label={`${lineLabel(key)} change`}
                value={part.op}
                onChange={(event) => setPart(key, { op: event.target.value })}
                onKeyDown={onKeyDown}
              >
                {ops.map((op) => (
                  <option key={op.key} value={op.key}>
                    {compact ? op.short : op.label}
                  </option>
                ))}
              </select>
              <input
                type="number"
                className="bnf-filter-num"
                aria-label={`${lineLabel(key)} amount`}
                placeholder={priced.pct_ops.includes(part.op) ? '%' : '$'}
                step="0.25"
                min="0"
                value={part.value}
                onChange={(event) =>
                  setPart(key, {
                    value: event.target.value,
                    plan_id: event.target.value ? autoLink(key, part) : part.plan_id,
                  })
                }
                onKeyDown={onKeyDown}
              />
              <select
                className="bnf-pv-requires"
                aria-label={`${lineLabel(key)} quote that has to sell`}
                value={part.plan_id ? String(part.plan_id) : ''}
                title="The quote that has to sell for this discount to be real"
                onChange={(event) => setPart(key, { plan_id: event.target.value ? Number(event.target.value) : null })}
                onKeyDown={onKeyDown}
              >
                <option value="">{`any ${carrier || 'carrier'} ${String(lineLabel(key)).toLowerCase()}`}</option>
                {(byLine[key] ?? []).map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.carrier_name} · {entry.name}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
      <div className="bnf-conc-total">
        {preview?.derived?.kind === 'bundle' ? (
          <>
            = <b>{preview.label}</b>
            {scope > 0 && (
              <>
                {' '}
                on {scope} {carrier} quote{scope === 1 ? '' : 's'}
              </>
            )}
            {requires && <span className="bnf-pv-requireline">requires {requires}</span>}
            {crossCarrier.length > 0 && (
              <span className="bnf-pv-crosswarn">
                {crossCarrier.join(' · ')} {crossCarrier.length === 1 ? 'is' : 'are'} not {carrier || 'this carrier'} —
                a bundling discount is normally that carrier’s own offer for placing more lines with them.
              </span>
            )}
          </>
        ) : (
          <span className="bnf-conc-was">Enter each placed line’s discount</span>
        )}
      </div>
    </div>
  );
}
