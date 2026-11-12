import BuilderCard from '../../shared/BuilderCard';
import ExperienceBlock from './ExperienceBlock';
import { pageMissing, pageStatus, pagesSummary } from './dealCardsModel';

/*
 * Presentation pages (plan.md §8.14; J42, J45; the old PresentationPagesCard.jsx at 891f1b3, same classes): what the
 * Presentation format prints for this client, page by page, and why a page would not — the ledger, with Fix ▸ to the
 * card that puts it right — and the plan experience. A ledger, never a gate: a page with nothing to say does not print,
 * and nothing here stops a download. The switches write `output.pages.<page>`; the ledger's facts are the server's
 * (`ledger`), and the switch is read live, so a toggle needs no re-read. The firm's pages (About, team, calendar, bios)
 * have no home until slices 29 and 34, so their rows have no Fix ▸ yet; team picks (J43) and renewal history (J44)
 * wait. The old card had no completed mark; this one takes one but never counts toward "n of N completed".
 */
export default function PagesCard({ ledger, output, experience, meta, card, busy, onSet, onFix }) {
  const pages = output.pages;
  return (
    <BuilderCard guide="build-pages" title="Presentation pages" summary={pagesSummary(ledger, pages)} card={card}>
      <div className="bb-panel-sub">
        What the Presentation format prints for this client, page by page, and why a page would not. A page with
        nothing to say does not print, and nothing here stops a download.
      </div>
      <div className="bnf-present-ledger">
        {ledger.map((row) => {
          const missing = pageMissing(row, pages);
          return (
            <div key={row.key} className={`bnf-present-row${missing ? ' bnf-present-row-missing' : ''}`}>
              {row.switchable ? (
                <label className="bnf-output-check">
                  <input
                    type="checkbox"
                    checked={pages[row.key] !== false}
                    disabled={busy}
                    onChange={(event) => onSet(`output.pages.${row.key}`, event.target.checked)}
                  />
                  {row.label}
                </label>
              ) : (
                <span className="bnf-output-check bnf-present-fixed">{row.label}</span>
              )}
              <span className="bnf-present-status">{pageStatus(row, pages)}</span>
              {missing && row.fix && (
                <button type="button" className="bnf-override-link" onClick={() => onFix({ fix: row.fix })}>
                  Fix ▸
                </button>
              )}
            </div>
          );
        })}
      </div>
      <div className="bnf-output-hint">
        The firm&apos;s story, team and meeting calendar apply to every proposal; they arrive with the firm&apos;s pages.
      </div>
      <ExperienceBlock key={JSON.stringify(experience)} experience={experience} meta={meta} busy={busy} onSet={onSet} />
    </BuilderCard>
  );
}
