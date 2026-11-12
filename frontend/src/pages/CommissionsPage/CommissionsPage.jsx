import { Navigate, useSearchParams } from 'react-router';
import { useAuth } from '../../auth/useAuth';
import PartiesTab from './PartiesTab';
import SettingsTab from './SettingsTab';

/*
 * /commissions (plan.md §8.18; H42, H48, H95–H102; 891f1b3 `commissions/CommissionsDashboard.jsx`, its words and
 * classes): open to a commission tier; "Commissions" for the all tier, "My commissions" for the own tier. Slice 48
 * builds the Producers & partners and Settings tabs (Settings is the all tier's); the tiles, the Book and By person
 * join with slice 49, and the ledger's tabs wait (OQ6). Tabs live in `?tab=`; an own-tier user asking for Settings
 * gets Producers & partners.
 */
const TABS = [
  { key: 'parties', label: 'Producers & partners', all: false },
  { key: 'settings', label: 'Settings', all: true },
];

export default function CommissionsPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tier = user.commissions_access;
  const isAll = tier === 'all';
  if (tier === 'none') return <Navigate to="/" replace />;

  const shown = TABS.filter((tab) => isAll || !tab.all);
  const asked = params.get('tab');
  const tab = shown.some((entry) => entry.key === asked) ? asked : shown[0].key;
  const setTab = (key) => {
    const next = new URLSearchParams(params);
    if (key === shown[0].key) next.delete('tab');
    else next.set('tab', key);
    setParams(next, { replace: true });
  };

  return (
    <div className="bb-dash">
      <div className="bb-dash-header">
        <div>
          <h1>{isAll ? 'Commissions' : 'My commissions'}</h1>
          <div className="bb-subtitle">
            {isAll
              ? 'Who gets what share of each client’s commission — booked when a deal sells, frozen from then on.'
              : 'Your share of every deal you are on, booked when it sold.'}
          </div>
        </div>
      </div>

      <div className="bnf-com-tabs" role="tablist" data-guide="commissions-tabs">
        {shown.map((entry) => (
          <button
            key={entry.key}
            type="button"
            role="tab"
            aria-selected={tab === entry.key}
            className={`bnf-com-tab ${tab === entry.key ? 'active' : ''}`}
            onClick={() => setTab(entry.key)}
          >
            {entry.label}
          </button>
        ))}
      </div>

      {tab === 'parties' && <PartiesTab isAll={isAll} />}
      {tab === 'settings' && isAll && <SettingsTab />}
    </div>
  );
}
