import { useSetIntent } from '../../api/intake';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';

/*
 * Lines to quote (B32): one chip per line, on for the lines on the shopping list. The old Intake tab's chip row
 * (891f1b3, `bnf-multi-chips`), same look; a chip writes through intake's intent door (`shop`), the one writer of the
 * lines to quote, so the coverage card above shows the change at once (B17).
 */
const NOTE_GAP = { marginTop: 8 }; // the old note's inline gap

export default function LinesToQuote({ deal, meta }) {
  const toast = useToast();
  const intent = useSetIntent(deal.id);
  const chosen = new Set(deal.requested_lines || []);

  function toggle(key) {
    if (intent.isPending) return;
    intent.mutate(
      { line: key, shop: !chosen.has(key) },
      { onError: (error) => toast.error(errorText(error, { fallback: 'Could not update the requested lines.' })) },
    );
  }

  return (
    <div className="bb-panel bnf-intake-section">
      <div className="bb-panel-title">Lines to quote</div>
      <div className="bb-panel-sub">Drives which carrier forms get assigned</div>
      <div className="bnf-multi-chips" role="group" aria-label="Lines to quote">
        {(meta?.lines || []).map((line) => (
          <span
            key={line.key}
            role="button"
            tabIndex={0}
            aria-pressed={chosen.has(line.key)}
            className={`bnf-chip ${chosen.has(line.key) ? 'bnf-chip-on' : ''}`}
            onClick={() => toggle(line.key)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                toggle(line.key);
              }
            }}
          >
            {line.label}
          </span>
        ))}
      </div>
      <div className="bb-drop-meta" style={NOTE_GAP}>
        The commission we agree with the carrier per line, and who gets what among our producers, live on the{' '}
        <b>Commission</b> tab — Intake is what we learn from the client.
      </div>
    </div>
  );
}
