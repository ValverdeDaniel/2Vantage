import { Fragment } from 'react';
import { Link } from 'react-router';
import { useDealForms } from '../../api/questionnaire';
import { navGroups } from './nav';
import { BUILT_TABS } from './tabs';

/**
 * The deal workspace's 232 px sticky sidebar (A20, A21; plan.md §8.4; CaseWorkspace.jsx at 891f1b3): "← Benefits",
 * the client's name, "Renews <effective date>", then the grouped nav in the old order. The intake ready chip (B33),
 * the client block (slice 67), badges and the readiness meters (slice 61) are not built yet.
 */
export default function DealSidebar({ deal, tab }) {
  // The Questionnaire tab shows only while the deal has a form, armed or started (G7; slice 42), or while it is open.
  const forms = useDealForms(deal.id);
  const hasForm = Boolean(forms.data?.forms?.length) || tab === 'questionnaire';
  const shown = BUILT_TABS.filter((key) => key !== 'questionnaire' || hasForm);
  return (
    <div className="bb-sidebar">
      <Link className="bb-back-link" to="/">
        ← Benefits
      </Link>
      <div className="bb-sidebar-account">
        <div className="bb-sidebar-name">{deal.client.name}</div>
        {deal.effective_date && <div className="bb-sidebar-policy bb-mono">Renews {deal.effective_date}</div>}
      </div>
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
              </Link>
            ))}
          </Fragment>
        ))}
      </nav>
    </div>
  );
}
