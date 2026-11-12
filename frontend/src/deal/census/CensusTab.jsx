import { useState } from 'react';
import { useCensus, useCensusImport, useStartImport } from '../../api/census';
import { useMeta } from '../../api/meta';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import EmptyState from '../../ui/EmptyState';
import InlineError from '../../ui/InlineError';
import Loading from '../../ui/Loading';
import { useToast } from '../../ui/useToast';
import CensusCounts from './CensusCounts';
import ImportDoor from './ImportDoor';
import MappingDialog from './MappingDialog';
import { lastApplied, waitingImport } from './mapping';

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

function Roster({ deal, meta, census, waiting, onReview }) {
  const toast = useToast();
  const remap = useStartImport(deal.id);
  const { summary } = census;
  const applied = lastApplied(census.imports);
  return (
    <div className="bb-tab-page bb-sov-page">
      <div className="bb-sov-header">
        <div>
          <div className="bb-tab-title">Roster</div>
          <div className="bb-subtitle">
            {summary.employees} employees · {summary.dependents} dependents · {summary.readiness_pct}% ready
            {summary.ok ? ' · Census OK' : ` · ${summary.missing_required} required cells blank`}
          </div>
        </div>
        <div className="bb-toolbar-actions">
          {applied && (
            <Button
              size="sm"
              busy={remap.isPending}
              onClick={() =>
                remap.mutate(
                  { documentId: applied.document_id },
                  {
                    onSuccess: (imp) => onReview(imp.id),
                    onError: (error) => toast.error(errorText(error)),
                  },
                )
              }
            >
              ⟲ Re-map source file
            </Button>
          )}
        </div>
      </div>
      {summary.errors > 0 && (
        <div className="bb-warn-banner">
          <span className="bb-warn-icon">⚠</span>
          <div>
            <b>
              {summary.errors} validation error{summary.errors === 1 ? '' : 's'}
            </b>{' '}
            in the census. Carriers will reject these rows.
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
      <ImportDoor
        dealId={deal.id}
        meta={meta}
        onStarted={(imp) => onReview(imp.id)}
        label="Import another census file ▸"
        primary={false}
      />
      <CensusCounts meta={meta} rollup={census.rollup} derived={census.derived} />
      {/* The roster grid (paged by employee, line chips, ✎ Edit, marks and asks) arrives with slice 41. */}
      <EmptyState title="The roster grid is on its way.">
        The people are on file and counted above; editing them person by person, cell by cell, comes next.
      </EmptyState>
    </div>
  );
}

/*
 * The Census tab (plan.md §8.10; Part C), in the old tab's frame (891f1b3 `CensusTab.jsx`). Slice 12 builds the way a
 * file gets in — the import door, the mapping dialog with its reformat banner and the dry run (C12–C17) — and the
 * counts the old tab showed above its roster: people, readiness, validation errors and a mapped file waiting. A waiting
 * mapping takes over the tab on an empty roster, as the old one did; with a roster it waits behind its banner. The
 * roster grid, its pills (Roster · Board · Request · Review), COBRA and the template are slices 41, 57 and 53.
 */
export default function CensusTab({ deal }) {
  const meta = useMeta().data;
  const census = useCensus(deal.id);
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
  if (hasRoster) return <Roster deal={deal} meta={meta} census={data} waiting={waiting} onReview={setReviewing} />;
  return (
    <div className="bb-tab-page">
      <div className="bb-tab-title">Census</div>
      <div className="bb-subtitle bb-mb-lg">
        Bring in the client&apos;s census — any layout. Its columns are mapped to the canonical schema, validated, and
        made exportable to any carrier template.
      </div>
      <ImportDoor dealId={deal.id} meta={meta} onStarted={(imp) => setReviewing(imp.id)} />
    </div>
  );
}
