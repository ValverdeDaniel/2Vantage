import { Fragment } from 'react';
import { Link } from 'react-router';
import { relationshipLabel } from '../../api/meta';
import { statusBadgeClass } from '../../lib/dealLook';
import { formatDate } from '../../lib/format';
import { backLink, clientNavGroups, clientPath, navBadges, rollupChip } from './clientTabs';
import PlanYearBlock from './PlanYearBlock';

const ARCHIVED_TIP = 'Off every list until restored; nothing was deleted';

/**
 * The client page's sticky sidebar (plan.md §8.5; CL13, CL14; old ClientWorkspace.jsx's `clientHead` at 891f1b3):
 * "← Clients" ("← Prospects" for a prospect); the name, "Owner <name>" or "No primary producer", "Effective <date>";
 * chips for the status, Archived and the agenda rollup (N overdue / N due soon / on track, from the client Agenda's
 * rollup, which the Overview's read carries as its Agenda tile); the nav in the old groups (`clientTabs.js`) with the
 * Agenda's overdue count (rose) and the Commissions "1" (amber) while no primary producer is set (slice 68); then the
 * Plan year block. "Year N with us", Inactive and P&C wait with renewals or are dropped (CL27, CL28).
 */
export default function ClientSidebar({ client, overview, tab, meta }) {
  const back = backLink(client.relationship);
  const effective = overview.tiles.effective;
  const chip = rollupChip(overview.tiles.agenda);
  const badges = navBadges(client, overview.tiles.agenda);
  return (
    <div className="bb-sidebar bnf-cw-sidebar">
      <Link className="bb-back-link" to={back.to}>
        {back.label}
      </Link>
      <div className="bb-sidebar-account">
        <div className="bb-sidebar-name">{client.name}</div>
        <div className="bb-sidebar-sub">{client.owner ? `Owner ${client.owner.name}` : 'No primary producer'}</div>
        {effective && <div className="bb-sidebar-policy bb-mono">Effective {formatDate(effective.date)}</div>}
        <div className="bnf-cw-sidechips">
          <span className={statusBadgeClass(client.relationship)} title="Client status">
            {relationshipLabel(meta, client.relationship)}
          </span>
          {client.archived && (
            <span className="bb-badge bb-badge-gray" title={ARCHIVED_TIP}>
              Archived
            </span>
          )}
          <span className={chip.className}>{chip.label}</span>
        </div>
      </div>
      <nav className="bb-nav" aria-label="Client sections">
        {clientNavGroups().map((group) => (
          <Fragment key={group.label || 'top'}>
            {group.label && <div className="bnf-nav-group-label">{group.label}</div>}
            {group.tabs.map((item) => (
              <Link
                key={item.key}
                to={clientPath(client.id, item.key)}
                className={`bb-nav-item bnf-cw-navbtn${item.key === tab ? ' active' : ''}`}
                aria-current={item.key === tab ? 'page' : undefined}
              >
                {item.label}
                {badges[item.key]?.count > 0 && (
                  <span className={`bb-nav-badge bb-nav-badge-${badges[item.key].tone}`}>{badges[item.key].count}</span>
                )}
              </Link>
            ))}
          </Fragment>
        ))}
      </nav>
      <PlanYearBlock overview={overview} />
    </div>
  );
}
