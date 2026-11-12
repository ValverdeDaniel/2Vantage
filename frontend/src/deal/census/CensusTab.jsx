import { useState } from 'react';
import { addMember, useCensus, useCensusImport } from '../../api/census';
import { useMeta } from '../../api/meta';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { CensusLens } from '../rfp';
import { useToast } from '../../ui/useToast';
import CobraCheck from './CobraCheck';
import ImportDoor from './ImportDoor';
import MappingDialog from './MappingDialog';
import { waitingImport } from './mapping';
import Roster from './Roster';

function ImportReview({ deal, meta, importId, hasRoster, onClose }) {
  const imp = useCensusImport(deal.id, importId);
  if (imp.isPending) return <Loading label="Reading the census file…" />;
  if (imp.isError) return <InlineError title="Census file" error={imp.error} onRetry={() => imp.refetch()} />;
  return (
    <MappingDialog
      key={imp.data.id}
      dealId={deal.id}
      imp={imp.data}
      meta={meta}
      hasRoster={hasRoster}
      onClose={onClose}
    />
  );
}

function RosterPage({ deal, meta, census, waiting, onReview, onPage, refetch }) {
  const { summary } = census;
  return (
    <div className="bb-tab-page bb-sov-page">
      <div className="bb-sov-header">
        <div>
          <div className="bb-tab-title">Roster</div>
          <div className="bb-subtitle">
            {summary.employees} employees · {summary.dependents} dependents · {summary.readiness_pct}% ready
            {summary.ok ? ' · Census OK' : ` · ${summary.missing_required} required cells blank`} · press ✎ Edit to
            change values, then work it like a spreadsheet: click a cell and type, Tab moves right, Enter moves down.
            Red underlines are validation errors, amber are warnings.
          </div>
        </div>
      </div>
      {summary.errors > 0 && (
        <div className="bb-warn-banner">
          <span className="bb-warn-icon">⚠</span>
          <div>
            <b>
              {summary.errors} validation error{summary.errors === 1 ? '' : 's'}
            </b>{' '}
            in the census — hover a red cell to see why. Carriers will reject these rows.
          </div>
        </div>
      )}
      {waiting && (
        <div className="bnf-staged-banner">
          <strong>A census file is mapped and waiting.</strong>{' '}
          {waiting.document_name ? `“${waiting.document_name}”` : 'A file'} came in on this deal and its columns are
          mapped — nothing on the roster has changed.{' '}
          <button type="button" className="bnf-override-link" onClick={() => onReview(waiting.id)}>
            Review the mapping ▸
          </button>
        </div>
      )}
      {/* The carrier formats' readiness and lens (slice 45, K79–K89): "Our census" is this roster. */}
      <CensusLens dealId={deal.id}>
        <Roster deal={deal} meta={meta} census={census} onPage={onPage} onReview={onReview} refetch={refetch} />
      </CensusLens>
    </div>
  );
}

function FirstByHand({ dealId, onAdded }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  return (
    <Button
      size="sm"
      busy={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await addMember(dealId, { kind: 'employee' });
          await onAdded();
        } catch (error) {
          toast.error(errorText(error));
        } finally {
          setBusy(false);
        }
      }}
    >
      ＋ Add the first employee by hand
    </Button>
  );
}

/*
 * The Census tab (plan.md §8.10; Part C), in the old tab's frame (891f1b3 `CensusTab.jsx`). Slice 12 builds the way a
 * file gets in — the import door, the mapping dialog with its reformat banner and the dry run (C12–C17) — and the
 * counts the old tab showed above its roster: people, readiness, validation errors and a mapped file waiting. A waiting
 * mapping takes over the tab on an empty roster, as the old one did; with a roster it waits behind its banner. The
 * roster grid (Roster.jsx: ✎ Edit, Excel keys, marks, COBRA, the template and export) is slice 41's; its pills
 * (Roster · Board · Request · Review) are slices 53 and 57. An empty roster offers the COBRA tick, the import door and
 * hand entry.
 */
export default function CensusTab({ deal }) {
  const meta = useMeta().data;
  const [page, setPage] = useState(1);
  const census = useCensus(deal.id, { page });
  const [reviewing, setReviewing] = useState(null);
  const [setAside, setSetAside] = useState(null);
  if (census.isPending) return <Loading label="Loading the census…" />;
  if (census.isError) return <InlineError title="Census" error={census.error} onRetry={() => census.refetch()} />;
  const data = census.data;
  const waiting = waitingImport(data.imports);
  const hasRoster = data.summary.employees + data.summary.dependents > 0;
  const opens = waiting && waiting.id !== setAside && (!hasRoster || waiting.reformatted || waiting.needs_attention);
  const open = reviewing || (opens ? waiting.id : null);
  const close = () => {
    setSetAside(open);
    setReviewing(null);
  };
  if (open) return <ImportReview deal={deal} meta={meta} importId={open} hasRoster={hasRoster} onClose={close} />;
  if (hasRoster) {
    return (
      <RosterPage
        deal={deal}
        meta={meta}
        census={data}
        waiting={waiting}
        onReview={setReviewing}
        onPage={setPage}
        refetch={() => census.refetch()}
      />
    );
  }
  return (
    <div className="bb-tab-page">
      <div className="bb-tab-title">Census</div>
      <div className="bb-subtitle bb-mb-lg">
        Bring in the client&apos;s census — any layout. Its columns are mapped to the canonical schema, validated, and
        made exportable to any carrier template.
      </div>
      {/* Worth saying before the roster arrives, which is when the client is still being asked for it (old app). */}
      <CobraCheck dealId={deal.id} cobra={data.cobra} onChanged={() => census.refetch()} />
      <ImportDoor dealId={deal.id} meta={meta} onStarted={(imp) => setReviewing(imp.id)}>
        <FirstByHand dealId={deal.id} onAdded={() => census.refetch()} />
      </ImportDoor>
    </div>
  );
}
