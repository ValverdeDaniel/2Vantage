import { useRfpChecks } from '../../../api/rfp';
import BuilderCard from '../../shared/BuilderCard';
import useRfpDownload from '../useRfpDownload';
import CensusRow from './CensusRow';
import FileRow from './FileRow';
import NoticeRow from './NoticeRow';
import PacketFooter from './PacketFooter';
import { packetSummary, sectionRows } from './packetModel';
import TriTick from './TriTick';

const HEADS = ['Document', 'Format', 'For'];
const DOWNLOAD_ONLY = 'Download only — attach one by hand when a carrier wants the roster on the form itself.';

/*
 * 4 · RFP packet (plan.md §8.12, §9.10; K34–K56; old CarriersTab.jsx at 891f1b3, `bnf-rfp-grid` markup as is): one
 * table in the old sections — carrier census formats, Warner's forms with the census inside (download only), carrier
 * questionnaires & disclosures (with "Not set up" when a kind has no form), the request form & proposal documents, the
 * attachments from the file — "The whole RFP" three-state box, a box per section, a pill per row from one checks call
 * asked again only when `checks_stamp` moves (K52), and the zip at its foot. A tick writes only what differs from the
 * recommendation (K35), shows at once and takes the card's completed mark off (K10). Every download opens the check
 * first (K51, K69).
 */
export default function PacketCard({ dealId, title, packet, stamp, card, onTicks, onForm, onOpenChecklist }) {
  const files = useRfpDownload(dealId);
  const checks = useRfpChecks(dealId, stamp);
  const pills = checks.data?.cards || {};
  const rows = packet?.rows || [];
  const set = (include) => onTicks({ include });
  const sections = (packet?.sections || []).filter(
    (section) => sectionRows(packet, section.key).length || section.key === 'questionnaires',
  );
  const row = (found) => {
    const props = { dealId, row: found, pill: pills[found.key], onSet: set, files };
    if (found.section === 'census') return <CensusRow key={found.key} {...props} />;
    return <FileRow key={found.key} {...props} onForm={onForm} />;
  };
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
            {sections.map((section) => {
              const found = sectionRows(packet, section.key);
              return (
                <tbody key={section.key} data-guide={`rfp-section-${section.key}`}>
                  <tr className="bnf-rfp-section">
                    <td colSpan={7}>
                      <span className="bnf-rfp-section-title">{section.title}</span>
                      {section.key === 'census_forms' ? (
                        <span className="bnf-review-note">{DOWNLOAD_ONLY}</span>
                      ) : (
                        <TriTick guide={`rfp-ticks-${section.key}`} rows={found} onSet={set} />
                      )}
                    </td>
                  </tr>
                  {found.map(row)}
                  {section.key === 'questionnaires' &&
                    (packet.notices || []).map((notice) => (
                      <NoticeRow key={notice.kind} notice={notice} onOpenChecklist={onOpenChecklist} />
                    ))}
                </tbody>
              );
            })}
          </table>
        </div>
      </div>
      <PacketFooter packet={packet} files={files} onReset={() => onTicks({ include: 'reset' })} />
      {files.modal}
    </BuilderCard>
  );
}
