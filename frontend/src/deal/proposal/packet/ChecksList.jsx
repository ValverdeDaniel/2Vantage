import { levelWord } from './packetModel';

/*
 * "Before you export" on the packet card (plan.md §8.15; J100; the old ProposalPacketCard's list at 891f1b3): the
 * builder's own checks (proposals/checks.py), Stops first. Fixing happens in the builder, which the card links to.
 */
export default function ChecksList({ checks }) {
  if (!checks?.length) return null;
  return (
    <div className="bnf-build-checks" role="region" aria-label="Before you export">
      <div className="bnf-build-checks-head">
        <b>Before you export</b>
        <span className="bb-drop-meta">
          What would print wrong in the PDF, the PowerPoint or the client spreadsheet. Fix anything marked Stops before
          a client sees it; the rest is yours to judge.
        </span>
      </div>
      <ul className="bnf-build-checks-list">
        {checks.map((item, i) => (
          <li key={`${item.code}-${item.line}-${i}`} className={`bnf-build-check bnf-build-check-${item.level}`}>
            <span className="bnf-build-check-level">{levelWord(item.level)}</span>
            <span className="bnf-build-check-msg">{item.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
