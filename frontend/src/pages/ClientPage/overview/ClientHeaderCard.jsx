import { Link } from 'react-router';
import { relationshipLabel, stageLabel } from '../../../api/meta';
import { initialsOf } from '../../../lib/dealLook';
import { formatDate } from '../../../lib/format';
import ClientFacts from './ClientFacts';
import { dayWords } from './clientView';

// The status chip in the old header's chip classes (§8.5): New client wears the old "First year" chip, Existing client
// the old "Renewal client" chip, a Prospect grey.
const STATUS_CHIPS = {
  new_client: 'bnf-cat-chip bnf-cat-static bnf-cat-custom',
  existing_client: 'bnf-cat-chip bnf-cat-static bnf-cat-renewal',
  prospect: 'bb-badge bb-badge-gray',
};

// The client box (old `bnf-ov-clientbox`): the deal in flight, "<year> deal ↗" with its stage pill and "Next: …" (the
// journey's next step), or "No deal in flight" with "Last sold …". Start renewal waits with renewals (H104).
function DealBox({ overview, journey, meta }) {
  const { current, last_sold: sold } = overview;
  if (!current) {
    return (
      <div className="bnf-ov-clientbox">
        <div className="bb-drop-meta bnf-ov-nolink">No deal in flight</div>
        {sold && (
          <div className="bnf-ov-clientnext">
            Last sold {sold.year}
            {sold.carriers.length ? ` · ${sold.carriers.join(', ')}` : ''}
          </div>
        )}
      </div>
    );
  }
  const next = journey?.next_step;
  return (
    <div className="bnf-ov-clientbox">
      <Link className="bnf-ov-clientlink" to={`/deals/${current.deal_id}/overview`}>
        {current.year} deal ↗
      </Link>
      <div className="bnf-ov-clientmeta">
        <span className="bb-stage-pill bnf-ov-stage">{stageLabel(meta, current.stage)}</span>
        {journey?.ready === 'submitted' && <span className="bb-badge bb-badge-green">at market</span>}
      </div>
      {next?.label && <div className="bnf-ov-clientnext">Next: {next.label}</div>}
    </div>
  );
}

/**
 * The client's header card (plan.md §8.5; CL16; old `ClientHeaderCard.jsx` at 891f1b3): the avatar, the name and the
 * standing brief's first line; chips for the status, "Client since", "Effective <date> · in Nd" and the owner; the
 * client box; then the facts (`ClientFacts`). The client dialog retired into it (CL26). "Year N with us", P&C and
 * Inactive wait with renewals or are dropped (CL27, CL28).
 */
export default function ClientHeaderCard({ client, overview, meta, writes, journey }) {
  const brief = (client.notes || '').trim().split('\n')[0].slice(0, 140);
  const effective = overview.tiles.effective;
  return (
    <div className="bb-panel bnf-ov-header">
      <div className="bnf-ov-identity">
        <div className="bb-avatar bnf-ov-avatar" aria-hidden="true">
          {initialsOf(client.name)}
        </div>
        <div className="bnf-ov-identity-main">
          <div className="bnf-ov-name">{client.name}</div>
          {brief && (
            <div className="bnf-ov-legal" title="Standing brief — edit on the Notes tab">
              {brief}
            </div>
          )}
          <div className="bnf-ov-chips">
            <span className={STATUS_CHIPS[client.relationship] || STATUS_CHIPS.prospect} title="Client status">
              {relationshipLabel(meta, client.relationship)}
            </span>
            {client.client_since && (
              <span className="bb-drop-meta">Client since {formatDate(client.client_since)}</span>
            )}
            {effective && (
              <span className="bb-drop-meta">
                Effective {formatDate(effective.date)} · {dayWords(effective.days)}
              </span>
            )}
            {client.owner && <span className="bb-drop-meta">Owner: {client.owner.name}</span>}
          </div>
        </div>
        <DealBox overview={overview} journey={journey} meta={meta} />
      </div>
      <ClientFacts client={client} overview={overview} meta={meta} writes={writes} />
    </div>
  );
}
