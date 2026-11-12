import { useState } from 'react';
import { Navigate, useSearchParams } from 'react-router';
import { useCommissionSettings, useRecords } from '../../api/commission';
import { useAuth } from '../../auth/useAuth';
import BookTab from './BookTab';
import ByPersonTab from './ByPersonTab';
import PartiesTab from './PartiesTab';
import SettingsTab from './SettingsTab';
import Tiles from './Tiles';

/*
 * /commissions (plan.md §8.18; H42–H48, H95–H102; 891f1b3 `commissions/CommissionsDashboard.jsx`, its words and
 * classes): open to a commission tier; "Commissions" for the all tier, "My commissions" for the own tier. The tiles
 * describe the Book's current filters (the whole book on the other tabs), the unconfirmed-defaults banner asks the
 * all tier to confirm (H47), and the tabs live in `?tab=` (H48): Book, By person, Producers & partners, Settings (the
 * all tier's; an own-tier user asking for it gets the Book). The ledger's tabs wait (OQ6).
 */
const TABS = [
  { key: 'book', label: 'Book', all: false },
  { key: 'people', label: 'By person', all: false },
  { key: 'parties', label: 'Producers & partners', all: false },
  { key: 'settings', label: 'Settings', all: true },
];
const LINKS = ['client', 'deal', 'party']; // `record` opens its drawer (BookTab), never a filter

function linksOf(linkKey) {
  return Object.fromEntries(linkKey.split('|').map((value, index) => [LINKS[index], value]));
}

export default function CommissionsPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tier = user.commissions_access;
  const isAll = tier === 'all';
  const shown = TABS.filter((tab) => isAll || !tab.all);
  const asked = params.get('tab');
  const tab = shown.some((entry) => entry.key === asked) ? asked : 'book';
  const linkKey = LINKS.map((key) => params.get(key) || '').join('|');
  const [filters, setFilters] = useState(() => ({ q: '', status: '', year: '', ...linksOf(linkKey) }));
  // A deep link (?client= / ?deal= / ?party=, e.g. By person's "book ↗") can change while the page stays mounted.
  const [seenLinks, setSeenLinks] = useState(linkKey);
  if (seenLinks !== linkKey) {
    setSeenLinks(linkKey);
    setFilters((current) => ({ ...current, ...linksOf(linkKey) }));
  }
  const book = useRecords(tab === 'book' ? filters : {}, { enabled: tier !== 'none' });
  const settings = useCommissionSettings();
  if (tier === 'none') return <Navigate to="/" replace />;

  const setTab = (key) => {
    const next = new URLSearchParams(params);
    if (key === 'book') next.delete('tab');
    else next.set('tab', key);
    setParams(next, { replace: true });
  };
  const unconfirmed = isAll && settings.data && !settings.data.confirmed;

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

      <Tiles totals={book.data?.totals} isAll={isAll} />

      {unconfirmed && (
        <div className="bnf-com-placeholder">
          Firm defaults are placeholders from the 8/18 call (producer {settings.data.first_year_pct}% year one /{' '}
          {settings.data.renewal_pct}% renewal). Confirm them on the{' '}
          <a
            href="?tab=settings"
            onClick={(event) => {
              event.preventDefault();
              setTab('settings');
            }}
          >
            Settings
          </a>{' '}
          tab.
        </div>
      )}

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

      {tab === 'book' && (
        <BookTab
          isAll={isAll}
          book={book}
          filters={filters}
          setFilters={setFilters}
          grouped={params.get('group') === 'client'}
        />
      )}
      {tab === 'people' && <ByPersonTab isAll={isAll} />}
      {tab === 'parties' && <PartiesTab isAll={isAll} />}
      {tab === 'settings' && isAll && <SettingsTab />}
    </div>
  );
}
