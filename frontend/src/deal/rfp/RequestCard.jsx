import CarrierChips from './CarrierChips';
import Chip from './Chip';
import RequestFields from './RequestFields';
import { bandWords, routeBody, toggleBody } from './requestModel';

/*
 * Card 2, "What we're requesting" (plan.md §8.12; K17–K29; old CarriersTab.jsx RequestPanel at 891f1b3, same markup,
 * classes and words): the band from the one headcount and the cross-check when the three counts differ (K17–K19); Send
 * through (the band's route is tagged "standard"; picking it again follows the band, K20); Funding to quote, where an
 * empty pick is kept and says so (K21, K22); the carrier chips (K23–K25); the commission the form prints (K29); then
 * Other carriers, Quotes due back and the notes (K26). Every control saves at once; none waits for another (K11).
 */
export default function RequestCard({ page, rfpMeta, onSave }) {
  const { request, band, enrollment, commission } = page;
  const funding = request.funding || [];
  const chooseRoute = (key) => {
    const body = routeBody(key, request);
    if (body) onSave(body);
  };
  return (
    <>
      <div className="bb-panel-sub">
        {bandWords(band)} · what we&apos;re shopping is the card above; these picks fill the cover (Warner&apos;s form
        or ours, by route) and decide which census files ride along.
      </div>
      {enrollment.warning && (
        <div className="bnf-rfp-rownote" role="status">
          <span className="bb-amber">⚠ {enrollment.warning}</span>
        </div>
      )}

      <div className="bnf-rfp-group" data-guide="carriers-route">
        <div className="bnf-rfp-group-label">Send through</div>
        <div className="bnf-rfp-chips" role="group" aria-label="Send through">
          {rfpMeta.routes.map((route) => (
            <Chip
              key={route.key}
              on={request.route === route.key}
              title={route.title}
              onClick={() => chooseRoute(route.key)}
            >
              {route.label}
              {route.key === request.route_default && <span className="bnf-rfp-chip-tag">{route.tag}</span>}
            </Chip>
          ))}
        </div>
      </div>

      <div className="bnf-rfp-group" data-guide="carriers-funding">
        <div className="bnf-rfp-group-label">Funding to quote</div>
        <div className="bnf-rfp-chips" role="group" aria-label="Funding to quote">
          {rfpMeta.funding.map((entry) => (
            <Chip
              key={entry.key}
              on={funding.includes(entry.key)}
              onClick={() => onSave(toggleBody('funding', entry.key, funding))}
            >
              {entry.label}
            </Chip>
          ))}
        </div>
        {funding.length === 0 && (
          <div className="bnf-rfp-rownote">
            <span className="bb-amber">{rfpMeta.no_funding}</span>
          </div>
        )}
      </div>

      <CarrierChips groups={rfpMeta.groups} chips={page.carriers} picked={request.carriers} onSave={onSave} />

      <div className="bnf-rfp-group" data-guide="carriers-commission">
        <div className="bnf-rfp-group-label">Commission requested</div>
        <div className="bnf-rfp-sub" title={commission.breakdown.join(' · ')}>
          {commission.text
            ? `${commission.text} — the agency's default rate, printed on the request form and in the emails`
            : "None set — the agency's default commission (Django admin, Agency settings) prints here once it is set"}
        </div>
      </div>

      <RequestFields request={request} limits={rfpMeta.limits} onSave={onSave} />
    </>
  );
}
