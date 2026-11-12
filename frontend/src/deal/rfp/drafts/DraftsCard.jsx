import { MarketButton } from '../../intake';
import BuilderCard from '../../shared/BuilderCard';
import useRfpDownload from '../useRfpDownload';
import useRfpSends from '../useRfpSends';
import DraftRow from './DraftRow';
import { copyText, draftsSummary, offersMarketed, routeWords } from './draftsModel';
import SentEarlier from './SentEarlier';

/*
 * 5 · Emails to send (plan.md §8.12, §9.11; K57–K68, K120, K121, K33; OQ52, OQ67, OQ82; old CarriersTab.jsx
 * CarrierDrafts at 891f1b3): drafted here and sent by a person from their own mailbox, never by the app. Through
 * Warner one draft to their quoting inbox; direct one per carrier. Copy, "Open in Outlook ⬇", the Sent tick (the
 * first moves the deal to Quoting; who was asked is what the proposal's Markets checked lists), "Sent earlier" with
 * Undo, and once something went out, intake's own Mark as marketed (same service, same gate, K33; it moves no stage).
 */
export default function DraftsCard({ deal, title, drafts, card, ready, marketedAt, toast }) {
  const files = useRfpDownload(deal.id);
  const sends = useRfpSends(deal.id);
  const rows = drafts?.rows || [];
  const copy = async (draft) => {
    try {
      await navigator.clipboard.writeText(copyText(draft));
      toast.success(`${draft.label} draft copied — paste it into your email`);
    } catch {
      toast.error('Could not copy — use “Open in Outlook” instead');
    }
  };
  return (
    <BuilderCard
      title={title}
      summary={draftsSummary(drafts)}
      card={card}
      guide="carriers-drafts"
      className="bnf-rfp-card bnf-rfp-drafts bb-mb"
    >
      <div className="bb-panel-sub">{routeWords(drafts?.route)}</div>
      {rows.length === 0 ? (
        <div className="bnf-rfp-rownote">Pick the carriers above — each one gets its own draft.</div>
      ) : (
        <div className="bnf-rfp-gridscroll">
          <table className="bnf-rfp-grid bnf-rfp-drafts-grid">
            <thead>
              <tr>
                <th>To</th>
                <th>Subject</th>
                <th>Attached</th>
                <th>Draft</th>
                <th>Sent</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((draft) => (
                <DraftRow
                  key={draft.key}
                  draft={draft}
                  files={files}
                  sending={sends.busy === draft.key}
                  onCopy={copy}
                  onSent={sends.mark}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <SentEarlier rows={drafts?.sent_earlier} sending={Boolean(sends.busy)} onUndo={(key) => sends.mark(key, false)} />
      {offersMarketed(drafts, marketedAt) && (
        <div className="bnf-rfp-rownote" data-guide="rfp-mark-marketed">
          Once it has all gone, mark the deal as sent to market — the step its readiness follows.{' '}
          <MarketButton deal={deal} ready={ready} />
        </div>
      )}
      {files.modal}
    </BuilderCard>
  );
}
