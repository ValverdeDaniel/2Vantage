import { Link } from 'react-router';
import { useEditRecord, useRebookRecord, useRecord } from '../../api/commission';
import { useMeta } from '../../api/meta';
import { errorText } from '../../lib/errors';
import { formatDate } from '../../lib/format';
import InlineError from '../../ui/InlineError';
import { useToast } from '../../ui/useToast';
import RecordFacts from './RecordFacts';
import RecordHistory from './RecordHistory';
import RecordShares from './RecordShares';

/*
 * One booked record (plan.md §8.18; H53–H57; 891f1b3 `commissions/RecordDrawer.jsx`, its words and classes): the
 * head (client · line · plan, the year chip, booked by, edited by, open deal ↗, the holes in words), Rebook from deal
 * (the all tier), the facts, the shares, the notes and, for the all tier, the history from Activity. The month strip
 * waits with the ledger (OQ6), and so does the comp agreement chip (H107).
 */
export default function RecordDrawer({ recordId, isAll, onClose }) {
  const toast = useToast();
  const meta = useMeta().data;
  const query = useRecord(recordId);
  const edit = useEditRecord();
  const rebook = useRebookRecord();

  if (query.isError) {
    return (
      <div className="bnf-com-drawer">
        <InlineError title="This record" error={query.error} onRetry={() => query.refetch()} />
      </div>
    );
  }
  if (!query.data) return <div className="bnf-com-drawer loading">Loading…</div>;
  const { record, history } = query.data;
  const holeWords = meta?.commission?.holes || {};

  function save(changes, done = 'Record updated') {
    edit.mutate(
      { id: record.id, changes },
      { onSuccess: () => toast.success(done), onError: (error) => toast.error(errorText(error)) },
    );
  }

  return (
    <div className="bnf-com-drawer" data-guide="record-drawer">
      <div className="bnf-com-drawer-head">
        <div>
          <div className="bnf-com-drawer-title">
            {record.client_name} · {record.line_label}
            {record.plan_label ? <span className="bb-drop-meta"> · {record.plan_label}</span> : null}
            {record.year_number ? (
              <span className="bb-badge bb-badge-gray" style={{ marginLeft: 8 }}>
                year {record.year_number}
              </span>
            ) : null}
          </div>
          <div className="bb-drop-meta">
            Booked {record.booked_at ? formatDate(record.booked_at) : '—'}
            {record.booked_by ? ` by ${record.booked_by}` : ''}
            {record.updated_by && record.updated_by !== record.booked_by ? ` · edited by ${record.updated_by}` : ''}
            {record.deal_id ? (
              <>
                {' · '}
                <Link to={`/deals/${record.deal_id}/commission`}>open deal ↗</Link>
              </>
            ) : null}
          </div>
          {record.holes.length > 0 && (
            <div className="bnf-com-holes">
              {record.holes.map((hole) => (
                <span key={hole} className="bb-badge bb-badge-amber">
                  {holeWords[hole]?.long || hole}
                </span>
              ))}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {isAll && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={rebook.isPending}
              title="Book again from the deal: every fact typed by hand keeps its value"
              onClick={() =>
                rebook.mutate(record.id, {
                  onSuccess: () => toast.success(record.deal_id ? 'Rebooked from the deal' : 'Rebooked'),
                  onError: (error) => toast.error(errorText(error)),
                })
              }
            >
              {record.deal_id ? 'Rebook from deal' : 'Rebook'}
            </button>
          )}
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Close
          </button>
        </div>
      </div>

      <RecordFacts record={record} isAll={isAll} onSave={save} />

      <div className="bnf-com-drawer-cols">
        <RecordShares key={JSON.stringify(record.shares)} record={record} isAll={isAll} />
        <div>
          <div className="bnf-com-section-title">Notes</div>
          {isAll ? (
            <textarea
              className="bnf-intake-input"
              aria-label="Notes"
              rows={3}
              defaultValue={record.notes}
              key={record.notes}
              onBlur={(event) => event.target.value !== record.notes && save({ notes: event.target.value }, 'Notes saved')}
            />
          ) : (
            <div className="bb-drop-meta" style={{ whiteSpace: 'pre-wrap' }}>
              {record.notes || '—'}
            </div>
          )}
          {isAll && <RecordHistory history={history} />}
        </div>
      </div>
    </div>
  );
}
