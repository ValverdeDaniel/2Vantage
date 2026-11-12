import TemplateBar from './TemplateBar';
import { layoutConfig, matchesConfig, rowsChanges, rowsConfig, summaryConfig } from './templateModel';

/*
 * The three TEMPLATE bars of the builder (plan.md §8.14; J68): what each saves from the builder payload and how
 * applying one writes the deal (one PATCH of several paths, `onApply`). The placeholders are the old ones (891f1b3).
 */

/** How the documents look: every `output` path; "Vantage default" reads as chosen while the deal matches it. */
export function LayoutTemplates({ output, busy, onApply }) {
  const current = layoutConfig(output);
  return (
    <TemplateBar
      kind="layout"
      kindLabel="Layout"
      current={current}
      matches={(config) => matchesConfig(current, config)}
      placeholders={{ name: 'Our standard look', purpose: 'Every option side by side, no agenda pages' }}
      busy={busy}
      onApply={onApply}
    />
  );
}

/** A line's rows and card stats, offered on this line or any line, applied on the line on screen. */
export function RowsTemplates({ line, busy, onApply }) {
  return (
    <TemplateBar
      kind="rows"
      kindLabel="Row set"
      line={line.line}
      lineLabel={line.label}
      current={rowsConfig(line.spec)}
      placeholders={{ name: 'Key medical rows', purpose: 'Deductible, coinsurance, out-of-pocket and Rx' }}
      busy={busy}
      onApply={(config) => onApply(rowsChanges(line.line, config))}
    />
  );
}

/** The executive summary: Show it and the picked figures. */
export function SummaryTemplates({ summary, busy, onApply }) {
  return (
    <TemplateBar
      kind="summary"
      kindLabel="Executive summary"
      current={summaryConfig(summary)}
      placeholders={{ name: 'Standard executive summary', purpose: 'Cost today, what we found, what it costs over a year' }}
      busy={busy}
      onApply={onApply}
    />
  );
}
