import { Fragment } from 'react';
import { Link } from 'react-router';
import { useJourney } from '../../api/agenda';
import { useDealForms } from '../../api/questionnaire';
import NavBadges from '../DealPage/NavBadges';
import { navGroups } from '../DealPage/nav';
import ReadinessMeters from '../DealPage/ReadinessMeters';
import { BUILT_TABS } from '../DealPage/tabs';

/**
 * The sidebar's "Plan year" block (plan.md §8.5; CL14; old ClientWorkspace.jsx at 891f1b3) without the year strip,
 * which waits with renewals (CL27): "<year> sections", the deal the page works in with the deal sidebar's nav in its
 * order, labels and badges (the shell's `journey/` read; Questionnaire while the deal has a form, G7), each item
 * opening that tab of the deal page (the old "Year overview" and "Year agenda" labels belong to the plan-year pages,
 * which wait with renewals: I9); then "This year at a glance", the deal's Intake, Census and Proposal meters. Nothing
 * for a client with no deal.
 */
export default function PlanYearBlock({ overview }) {
  const dealId = overview.deal_id;
  const journey = useJourney(dealId);
  const forms = useDealForms(dealId);
  if (!dealId) return null;
  const year = overview.history.find((row) => row.deal_id === dealId)?.year;
  const hasForm = Boolean(forms.data?.forms?.length);
  const shown = BUILT_TABS.filter((key) => key !== 'questionnaire' || hasForm);
  return (
    <>
      <div className="bnf-cw-year">
        <div className="bnf-cw-year-label">Plan year</div>
        <div className="bnf-cw-year-sub">{year ? `${year} sections` : 'Sections'}</div>
        <nav className="bb-nav" aria-label={`${year || 'This'} deal's sections`}>
          {navGroups(shown).map((group) => (
            <Fragment key={group.label || 'top'}>
              {group.label && <div className="bnf-nav-group-label">{group.label}</div>}
              {group.tabs.map((item) => (
                <Link key={item.key} to={`/deals/${dealId}/${item.key}`} className="bb-nav-item">
                  {item.label}
                  <NavBadges tab={item.key} badges={journey.data?.badges} />
                </Link>
              ))}
            </Fragment>
          ))}
        </nav>
      </div>
      <ReadinessMeters
        meters={journey.data?.meters}
        label="This year at a glance"
        order={['intake', 'census', 'proposal']}
      />
    </>
  );
}
