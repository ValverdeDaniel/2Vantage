import { useState } from 'react';
import BuilderCard from '../../shared/BuilderCard';
import { toggledHidden } from './dealCardsModel';

const QUOTED = { true: 'Yes', false: 'No', null: '–' };

/*
 * Markets checked (plan.md §8.14; J63, K117; the old markets card of ProposalBuilder.jsx at 891f1b3, same words and
 * classes): who we went to on this line and whether they quoted — one table per line, after the executive summary.
 * The carriers come from the emails marked sent on the RFP tab (`rfp.asked_by_line`) and the quotes on this deal; with
 * no RFP sent, only the carriers that quoted are listed and the table waits. Show it (deal-wide: true, false, or Back to
 * automatic), a note per carrier (≤120 characters, saved on blur) and a Show tick per carrier, each one path of
 * `markets` (J20). The rows, their order and the unmatched names are the server's (`markets`). A hidden carrier also
 * leaves the client spreadsheet's Compare and All Plans lists, and the card says so (J154; OQ39; slice 27).
 */
export default function MarketsCard({ markets, line, settings, meta, card, busy, onSet }) {
  const [notes, setNotes] = useState({});
  const entry = markets.lines.find((found) => found.key === line.line) || null;
  const hidden = settings.hidden;
  const path = (name) => `markets.lines.${line.line}.${name}`;
  return (
    <BuilderCard guide="build-markets" title="Markets checked" summary={markets.on ? 'Shown' : 'Not shown'} card={card}>
      <div className="bnf-build-head">
        <div className="bb-panel-sub">
          Who we went to and whether they quoted — one table per line, after the executive summary. The carriers come
          from the emails marked sent on the RFP page and the quotes on this deal.
        </div>
        <label className="bnf-filter-check">
          <input type="checkbox" disabled={busy} checked={markets.on} onChange={() => onSet('markets.on', !markets.on)} />
          Show it
        </label>
      </div>
      {markets.override !== null && (
        <button
          type="button"
          className="bnf-override-link"
          disabled={busy}
          title="Show it automatically once a send is recorded and a quote is back"
          onClick={() => onSet('markets.on', null)}
        >
          Back to automatic
        </button>
      )}
      {!markets.has_asks && (
        <div className="bb-drop-meta">
          No RFP email is marked sent yet, so only the carriers that quoted are listed. The table shows itself once a
          send is recorded and a quote is back.
        </div>
      )}
      {entry && entry.unmatched.length > 0 && (
        <div className="bb-drop-meta bnf-build-newhint">
          Not tied to a carrier you asked: {entry.unmatched.join(', ')} — check the carrier name on the quote before
          this reads &ldquo;No&rdquo;.
        </div>
      )}
      {entry ? (
        <table className="bnf-markets-table bnf-build-markets">
          <thead>
            <tr>
              <th>Carrier</th>
              <th>Quoted</th>
              <th>On this proposal</th>
              <th>Note for the client</th>
              <th>Show</th>
            </tr>
          </thead>
          <tbody>
            {entry.rows.map((row) => {
              const saved = settings.notes[row.id] || '';
              const off = hidden.includes(row.id);
              return (
                <tr key={row.id} className={off ? 'bnf-build-markets-hidden' : ''}>
                  <td>
                    {row.carrier}
                    {row.current && <span className="bnf-markets-current"> (Current)</span>}
                    {markets.has_asks && !row.current && !row.asked && (
                      <span className="bb-drop-meta"> · not on the RFP</span>
                    )}
                  </td>
                  <td>{QUOTED[String(row.quoted)] ?? '–'}</td>
                  <td>{row.presented ? 'Yes' : 'No'}</td>
                  <td>
                    <input
                      type="text"
                      className="bnf-intake-input"
                      maxLength={meta.limits.market_note}
                      aria-label={`Note for ${row.carrier}`}
                      value={notes[row.id] ?? saved}
                      placeholder={row.note_default || 'Competitive, not competitive, rate pass…'}
                      onChange={(event) => setNotes((now) => ({ ...now, [row.id]: event.target.value }))}
                      onBlur={() => {
                        const typed = notes[row.id];
                        if (typed !== undefined && typed.trim() !== saved) onSet(path(`notes.${row.id}`), typed.trim());
                        setNotes(({ [row.id]: _gone, ...rest }) => rest);
                      }}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={!off}
                      disabled={busy}
                      aria-label={`Show ${row.carrier} on the client’s table`}
                      title={off ? 'Hidden from the client' : 'On the client’s table'}
                      onChange={() => onSet(path('hidden'), toggledHidden(hidden, row.id))}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <div className="bb-empty">No carriers asked or quoted on this line yet.</div>
      )}
      {entry && hidden.length > 0 && (
        <div className="bb-drop-meta">
          A carrier hidden here also leaves the client spreadsheet&rsquo;s Compare and All Plans tabs: its quotes that are
          not on the proposal are not listed there.
        </div>
      )}
    </BuilderCard>
  );
}
