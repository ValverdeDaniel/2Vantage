import { useState } from 'react';
import { Link } from 'react-router';
import { useChecklistWrites } from '../../intake';
import CensusGroup from './CensusGroup';
import ConfirmGroup from './ConfirmGroup';
import DocumentsGroup from './DocumentsGroup';
import FormGroup from './FormGroup';
import { isOpen, marketButton, tabLink, toggled } from './gtmModel';
import IntakeGroup from './IntakeGroup';
import IntentGroup from './IntentGroup';
import ReqGroup from './ReqGroup';

/**
 * Card 1, Get to Market (plan.md §8.6; M42–M61, M67, M108–M111; old Vantage 891f1b3 `GetToMarketCard.jsx`): the
 * readiness badge, "Quotes came in first…" on a quote-first deal, "N of M requirements met · <tier>", then the
 * requirement groups, each open until met, and the footer's Send to market ▸ (or Open intake ▸) and Open census ▸.
 * Everything comes from the Overview's `get_to_market` block; every control writes through the app that owns it —
 * intake's checklist door, documents' upload, the questionnaire's form choice and review's request tray — and the
 * Overview reads the deal again after each one. The old "Show me how ▸" guide is dropped (M12).
 */
export default function GetToMarketCard({ deal, card, meta }) {
  const [toggles, setToggles] = useState({});
  const writes = useChecklistWrites(deal.id);
  const acceptOf = (kind) => (meta?.document_kinds || []).find((entry) => entry.key === kind)?.accept?.join(',') || '';
  const market = marketButton(deal.id, card);

  const body = (group) => {
    if (group.key === 'coverage') return <IntentGroup group={group} />;
    if (group.key === 'intake') return <IntakeGroup dealId={deal.id} group={group} />;
    if (group.key === 'census') return <CensusGroup dealId={deal.id} group={group} />;
    if (group.key === 'questionnaire' || group.key === 'stop_loss') {
      return <FormGroup deal={deal} meta={meta} group={group} writes={writes} accept={acceptOf(group.item.kind)} />;
    }
    if (group.key === 'documents') return <DocumentsGroup dealId={deal.id} group={group} writes={writes} acceptOf={acceptOf} />;
    return <ConfirmGroup dealId={deal.id} group={group} writes={writes} />;
  };

  return (
    <div className="bb-panel bnf-phase-card">
      <div className="bnf-phase-card-head">
        <div className="bb-panel-title">1 · Get to Market</div>
        <span className={`bnf-ready-badge bnf-ready-${card.badge}`}>{card.badge_label}</span>
      </div>
      <div className="bb-panel-sub">Collect the client&apos;s data once, then send the group to carriers.</div>
      {card.quotes_first && <div className="bnf-phase-skipped-note">{card.quotes_first}</div>}
      <div className="bnf-req-rollup bb-mono">
        {card.met} of {card.required} requirements met · {card.tier_label}
      </div>
      {card.groups.map((group) => (
        <ReqGroup
          key={group.key}
          group={group}
          open={isOpen(group, toggles)}
          onToggle={() => setToggles((state) => toggled(state, group))}
        >
          {body(group)}
        </ReqGroup>
      ))}
      <div className="bnf-phase-card-foot">
        <Link className="btn btn-primary btn-sm" to={market.to}>
          {market.label}
        </Link>
        <Link className="btn btn-secondary btn-sm" to={tabLink(deal.id, 'census')}>
          Open census ▸
        </Link>
      </div>
    </div>
  );
}
