import { RENEWAL, stageLabel } from '../../api/meta';
import { initialsOf } from '../../lib/dealLook';
import { formatDate } from '../../lib/format';
import ClientBox from './ClientBox';
import HeaderFacts from './HeaderFacts';

/**
 * The Overview's header (M13–M30; old Vantage 891f1b3 `overview/ClientHeader.jsx`): the avatar, the client's name and
 * its legal name when that differs; chips for the deal type (`deals.rules.deal_type`, M14), the stage, days open,
 * Renews, the owner and the carrier's renewal offer (M20, shown only when the letter's figures are on file); the
 * client box; then the click-to-edit facts. The P&C badge is dropped (M19); earlier deals wait with renewals (M22).
 */
export default function OverviewHeader({ deal, overview, meta }) {
  const { identity, renewal_offer: offer } = overview;
  const legal = identity.legal_name && identity.legal_name !== identity.name ? identity.legal_name : '';
  const days = identity.open_days;
  return (
    <div className="bb-panel bnf-ov-header">
      <div className="bnf-ov-identity">
        <div className="bb-avatar bnf-ov-avatar" aria-hidden="true">
          {initialsOf(identity.name)}
        </div>
        <div className="bnf-ov-identity-main">
          <div className="bnf-ov-name">{identity.name}</div>
          {legal && <div className="bnf-ov-legal">{legal}</div>}
          <div className="bnf-ov-chips">
            <span
              className={`bnf-cat-chip bnf-cat-static ${identity.type === RENEWAL ? 'bnf-cat-renewal' : 'bnf-cat-custom'}`}
            >
              {identity.type_label}
            </span>
            <span className="bb-stage-pill bnf-ov-stage">{stageLabel(meta, identity.stage)}</span>
            {days != null && (
              <span className="bb-drop-meta">
                Open {days} day{days === 1 ? '' : 's'}
              </span>
            )}
            {identity.renews && <span className="bb-drop-meta">Renews {formatDate(identity.renews)}</span>}
            {identity.owner && <span className="bb-drop-meta">Owner: {identity.owner.name}</span>}
            {offer && (
              <span
                className="bb-drop-meta"
                title="The carrier's as-offered renewal, from the letter's facts on this plan year"
              >
                {offer.label}
              </span>
            )}
          </div>
        </div>
        <ClientBox deal={deal} client={overview.client} meta={meta} />
      </div>
      <HeaderFacts deal={deal} overview={overview} meta={meta} />
    </div>
  );
}
