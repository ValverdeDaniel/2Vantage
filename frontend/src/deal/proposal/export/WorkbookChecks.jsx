import { useState } from 'react';
import { LEVEL, countWords, tabLevel } from './workbookModel';

/*
 * The tab's checks (plan.md §8.14; J118; the old WorkbookViewer checks strip at 891f1b3): "Medical All Plans: 5 cut
 * off · 4 tight", green when nothing is found, each check a button that selects its cell (`onGo`); six shown, then
 * "Show all N". A capped tab says how many rows the download has.
 */
export default function WorkbookChecks({ tab, checks, onGo }) {
  const [showAll, setShowAll] = useState(false);
  const level = tabLevel(tab.counts);
  const words = countWords(tab.counts);
  const shown = showAll ? checks : checks.slice(0, 6);
  return (
    <div className={`bnf-xv-fit bnf-xv-fit-${level || 'ok'} bnf-xw-checks`} role="status">
      <div>
        {words.length ? `${tab.title}: ${words.join(' · ')}` : `${tab.title}: no formula errors, no "####", no text cut off`}
        {tab.cut && (
          <span className="bnf-xw-capped">
            {' '}
            · rows 1–{tab.cut.shown} of {tab.cut.total} shown here; the download has them all
          </span>
        )}
      </div>
      {checks.length > 0 && (
        <ul className="bnf-xw-checklist">
          {shown.map((check) => (
            <li key={`${check.kind}-${check.cell}`}>
              <button type="button" className="bnf-xw-check" onClick={() => onGo(check)}>
                <span className={`bnf-xv-dot bnf-xv-dot-${LEVEL[check.kind]}`} aria-hidden="true" />
                <b>{check.cell}</b>
                {check.label ? ` · ${check.label}` : ''}
                {' — '}
                {check.text}
              </button>
            </li>
          ))}
          {checks.length > shown.length && (
            <li>
              <button type="button" className="bnf-refresh-retry" onClick={() => setShowAll(true)}>
                Show all {checks.length}
              </button>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
