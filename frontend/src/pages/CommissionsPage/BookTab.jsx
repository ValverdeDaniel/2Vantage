import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { BOOK_EXPORT_PATH, cleanFilters, useBookDeal, useParties } from '../../api/commission';
import { useMeta } from '../../api/meta';
import { errorText } from '../../lib/errors';
import { useDebouncedValue } from '../../lib/useDebouncedValue';
import ExportButton from '../../ui/ExportButton';
import InlineError from '../../ui/InlineError';
import { useToast } from '../../ui/useToast';
import AddToBookDialog from './AddToBookDialog';
import BookTable from './BookTable';
import RecordDrawer from './RecordDrawer';

/*
 * The Book (plan.md §8.18; H49–H51, H58; 891f1b3 `commissions/BookTab.jsx`, its words and classes): the filters
 * (search, waiting 300 ms; person, the all tier's; status, where void shows only when asked; year), the deal and
 * client links with their Clear, Rebook deal (the all tier, on a deal link), group by client, Export, and the all
 * tier's "＋ Add to book". A row opens its drawer. One answer per filter change carries the rows and the totals the
 * tiles show; past the server's cap the screen asks to narrow the filter. LOB goes (2V is benefits only).
 */
export default function BookTab({ isAll, book, filters, setFilters, grouped }) {
  const toast = useToast();
  const meta = useMeta().data;
  const [params, setParams] = useSearchParams();
  const [text, setText] = useState(filters.q);
  const [byClient, setByClient] = useState(grouped);
  const [adding, setAdding] = useState(false);
  const q = useDebouncedValue(text, 300);
  const parties = useParties(false);
  const rebook = useBookDeal(filters.deal);
  const openId = Number(params.get('record')) || null;

  useEffect(() => setFilters((current) => (current.q === q ? current : { ...current, q })), [q, setFilters]);
  const set = (patch) => setFilters((current) => ({ ...current, ...patch }));
  const openRecord = (id) => {
    const next = new URLSearchParams(params);
    if (id) next.set('record', id);
    else next.delete('record');
    setParams(next, { replace: true });
  };
  const clearLink = () => {
    set({ client: '', deal: '' });
    const next = new URLSearchParams(params);
    next.delete('client');
    next.delete('deal');
    setParams(next, { replace: true });
  };

  const rows = book.data?.rows;
  const people = [...(parties.data?.producers || []), ...(parties.data?.partners || [])].filter((p) => p.id);
  const statuses = meta?.commission?.statuses || [];
  return (
    <div>
      <div className="bnf-com-filters" data-guide="book-filters">
        <input
          placeholder="Search client, deal, carrier…"
          aria-label="Search the book"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        {isAll && (
          <select aria-label="Person" value={filters.party} onChange={(event) => set({ party: event.target.value })}>
            <option value="">All producers & partners</option>
            {people.map((person) => (
              <option key={person.id} value={person.id}>
                {person.name}
              </option>
            ))}
          </select>
        )}
        <select aria-label="Status" value={filters.status} onChange={(event) => set({ status: event.target.value })}>
          <option value="">Any status</option>
          {statuses.map((status) => (
            <option key={status.key} value={status.key}>
              {status.label}
            </option>
          ))}
        </select>
        <select aria-label="Year" value={filters.year} onChange={(event) => set({ year: event.target.value })}>
          <option value="">Any year</option>
          {(book.data?.years || []).map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
        {(filters.client || filters.deal) && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={clearLink}>
            Clear {filters.client ? 'client' : 'deal'} filter
          </button>
        )}
        {isAll && filters.deal && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            title="Book the deal again from its sale: every fact typed by hand keeps its value"
            disabled={rebook.isPending}
            onClick={() =>
              rebook.mutate(undefined, {
                onSuccess: (answer) => toast.success(`Rebooked ${answer.booked.length} record${answer.booked.length === 1 ? '' : 's'}`),
                onError: (error) => toast.error(errorText(error)),
              })
            }
          >
            Rebook deal
          </button>
        )}
        <label className="bnf-com-active" style={{ marginLeft: 'auto' }} data-guide="book-group">
          <input type="checkbox" checked={byClient} onChange={(event) => setByClient(event.target.checked)} /> group by
          client
        </label>
        <ExportButton
          path={BOOK_EXPORT_PATH}
          params={cleanFilters(filters)}
          fallbackName="commission-book.xlsx"
          title="Download the Book (with the current filters) as an Excel workbook"
        />
        {isAll && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAdding(true)}>
            ＋ Add to book
          </button>
        )}
      </div>

      {book.isError && <InlineError title="The Book" error={book.error} onRetry={() => book.refetch()} />}
      {!rows && !book.isError && <div className="loading">Loading…</div>}
      {rows && rows.length === 0 && (
        <div className="bnf-com-empty">
          Nothing booked yet. Records are created when a deal is marked sold — or book one by hand with ＋ Add to book.
        </div>
      )}
      {book.data?.capped && (
        <div className="bnf-com-placeholder">
          Showing the first {book.data.cap} records — narrow the filter to see the rest.
        </div>
      )}
      {rows && rows.length > 0 && (
        <BookTable
          rows={rows}
          sums={book.data.groups}
          grouped={byClient}
          isAll={isAll}
          openId={openId}
          onOpen={openRecord}
        />
      )}
      {openId && <RecordDrawer recordId={openId} isAll={isAll} onClose={() => openRecord(null)} />}
      {adding && <AddToBookDialog onClose={() => setAdding(false)} onAdded={(record) => openRecord(record.id)} />}
    </div>
  );
}
