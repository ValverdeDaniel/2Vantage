import { membersWords } from './packetModel';

/*
 * The zip of everything ticked above (plan.md §9.10; K54, K55; old CarriersTab.jsx at 891f1b3): what it holds, by
 * name; "↺ Reset to recommended" throws away every tick that differs from what the picks recommend (the old
 * "Recommended", renamed, X-183); "Download packet (N) ⬇" opens the check first, then builds the zip once.
 */
export default function PacketFooter({ packet, files, onReset }) {
  const count = packet?.count || 0;
  return (
    <div className="bnf-rfp-packet" data-guide="carriers-packet">
      <div>
        <div className="bnf-export-name">Download the packet</div>
        <div className="bb-panel-sub">{membersWords(packet)}</div>
      </div>
      <div className="bnf-export-actions">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          title="Throw away every tick that differs from what the carrier picks recommend"
          onClick={onReset}
        >
          ↺ Reset to recommended
        </button>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={count === 0 || files.busy === 'packet'}
          onClick={() => files.download('packet', 'RFP packet')}
        >
          {files.busy === 'packet' ? 'Building…' : `Download packet (${count}) ⬇`}
        </button>
      </div>
    </div>
  );
}
