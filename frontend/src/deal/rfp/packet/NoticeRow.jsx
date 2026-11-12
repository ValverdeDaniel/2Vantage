import { Tick } from './RowParts';

/*
 * "Not set up" (plan.md §8.12; K45; G111; old CarriersTab.jsx at 891f1b3): a kind of carrier form the deal has none of
 * says so, with the forms its picker offers, and opens the readiness checklist where the picker is (K15) — the old
 * "Open Overview ▸" pointed at a board this page now carries as card 3.
 */
export default function NoticeRow({ notice, onOpenChecklist }) {
  return (
    <tr data-guide={`rfp-questionnaire-${notice.kind}`} className="bnf-rfp-row-notice">
      <td className="bnf-rfp-col-tick">
        <Tick row={{ packet_eligible: false }} />
      </td>
      <td colSpan={5}>
        <div className="bnf-rfp-doc">
          {notice.title} <span className="bb-badge">Not set up</span>
        </div>
        <div className="bnf-rfp-sub">{notice.text}</div>
      </td>
      <td>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onOpenChecklist}>
          Open the checklist ▸
        </button>
      </td>
    </tr>
  );
}
