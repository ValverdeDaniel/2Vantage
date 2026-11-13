import { Fragment } from 'react';
import { Link } from 'react-router';
import { useJourney } from '../../api/agenda';
import { labelOf, PROSPECT, useMeta } from '../../api/meta';
import { useDealForms } from '../../api/questionnaire';
import { navGroups } from './nav';
import NavBadges from './NavBadges';
import ReadinessMeters from './ReadinessMeters';
import { BUILT_TABS } from './tabs';

// The ready chip's classes by intake's ready state (old READY_CHIP); its words are /api/meta/ `review.readiness`.
const READY_CLASSES = { blocked: 'bnf-ready-blocked', ready: 'bnf-ready-ready', submitted: 'bnf-ready-submitted' };

/**
 * The deal workspace's 232 px sticky sidebar (A20, A21, A23; plan.md §8.4; CaseWorkspace.jsx at 891f1b3): "← Benefits",
 * the client's name, "Renews <effective date>" and the intake ready chip (B33), then the grouped nav in the old order
 * with its badges, and the Deal readiness meters (slice 61, from agenda's `journey/`). Between them, for a New or
 * Existing client, the client block "<client> ↗" opens the client page (A20, CL26; slice 67), as the old block showed
 * only for a deal linked to a client; the year strip waits with renewals.
 */
export default function DealSidebar({ deal, tab }) {
  // The Questionnaire tab shows only while the deal has a form, armed or started (G7; slice 42), or while it is open.
  const forms = useDealForms(deal.id);
  const journey = useJourney(deal.id);
  const meta = useMeta();
  const hasForm = Boolean(forms.data?.forms?.length) || tab === 'questionnaire';
  const shown = BUILT_TABS.filter((key) => key !== 'questionnaire' || hasForm);
  const ready = journey.data?.ready;
  return (
    <div className="bb-sidebar">
      <Link className="bb-back-link" to="/">
        ← Benefits
      </Link>
      <div className="bb-sidebar-account">
        <div className="bb-sidebar-name">{deal.client.name}</div>
        {deal.effective_date && <div className="bb-sidebar-policy bb-mono">Renews {deal.effective_date}</div>}
        {ready && READY_CLASSES[ready] && (
          <span className={`bnf-ready-badge bnf-ready-badge-sm ${READY_CLASSES[ready]}`}>
            {labelOf(meta.data?.review?.readiness, ready)}
          </span>
        )}
      </div>
      {deal.client.relationship !== PROSPECT && (
        <div className="bnf-case-client">
          <Link className="bnf-case-client-link" to={`/clients/${deal.client.id}/overview`}>
            {deal.client.name} ↗
          </Link>
        </div>
      )}
      <nav className="bb-nav" aria-label="Deal sections">
        {navGroups(shown).map((group) => (
          <Fragment key={group.label || 'top'}>
            {group.label && <div className="bnf-nav-group-label">{group.label}</div>}
            {group.tabs.map((item) => (
              <Link
                key={item.key}
                to={`/deals/${deal.id}/${item.key}`}
                className={item.key === tab ? 'bb-nav-item active' : 'bb-nav-item'}
                aria-current={item.key === tab ? 'page' : undefined}
              >
                {item.label}
                <NavBadges tab={item.key} badges={journey.data?.badges} />
              </Link>
            ))}
          </Fragment>
        ))}
      </nav>
      <ReadinessMeters meters={journey.data?.meters} />
    </div>
  );
}
