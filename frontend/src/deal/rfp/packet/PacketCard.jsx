import BuilderCard from '../../shared/BuilderCard';
import useRfpDownload from '../useRfpDownload';
import CensusRow from './CensusRow';
import { packetSummary } from './packetModel';
import TriTick from './TriTick';

const HEADS = ['Document', 'Format', 'For'];

/*
 * 4 · RFP packet (plan.md §8.12, §9.10; K34–K42; old CarriersTab.jsx at 891f1b3, `bnf-rfp-grid` markup as is): one
 * table in sections, "The whole RFP" three-state box with Select all and Deselect all, and a box per section. Slice 45
 * draws the carrier census formats; the Warner forms with the census inside (K42), the questionnaires, the request form
 * and cover, the attachments and the packet download (K43–K56) join with slice 46. A tick writes only what differs from
 * the recommendation (K35), shows at once and takes the card's completed mark off (K10).
 */
export default function PacketCard({ dealId, title, packet, card, onTicks }) {
  const files = useRfpDownload(dealId);
  const rows = packet?.rows || [];
  const set = (include) => onTicks({ include });
  return (
    <BuilderCard
      title={title}
      summary={packetSummary(packet)}
      card={card}
      guide="rfp-packet"
      className="bnf-rfp-card bnf-rfp-packetcard bb-mb"
    >
      <div className="bb-grid-card bnf-rfp-gridcard">
        <div className="bnf-rfp-gridbar" data-guide="rfp-select-all">
          <TriTick rows={rows} onSet={set} label="The whole RFP" />
          <span className="bnf-review-note">
            Select all ticks every carrier-facing document. What is off on purpose stays off and says why; only what
            differs from the recommendation is recorded.
          </span>
        </div>
        <div className="bnf-rfp-gridscroll">
          <table className="bnf-rfp-grid" data-guide="rfp-grid">
            <thead>
              <tr>
                <th className="bnf-rfp-col-tick">In packet</th>
                {HEADS.map((head) => (
                  <th key={head}>{head}</th>
                ))}
                <th className="bnf-rfp-num">Rows</th>
                <th className="bnf-rfp-num">Check</th>
                <th>Download</th>
              </tr>
            </thead>
            <tbody data-guide="rfp-census-formats">
              <tr className="bnf-rfp-section">
                <td colSpan={7}>
                  <span className="bnf-rfp-section-title">Carrier census formats</span>
                  <TriTick guide="rfp-ticks-census" rows={rows} onSet={set} />
                </td>
              </tr>
              {rows.map((row) => (
                <CensusRow
                  key={row.key}
                  dealId={dealId}
                  row={row}
                  onSet={set}
                  downloading={files.busy === row.key}
                  onDownload={(found) => files.download(found.key, `census.${found.file_format}`)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </BuilderCard>
  );
}
