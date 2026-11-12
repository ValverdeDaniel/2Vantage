import { useState } from 'react';
import { useRfpFormat } from '../../../api/rfp';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import useRfpDownload from '../useRfpDownload';
import GapQueue from './GapQueue';
import LensColumns from './LensColumns';
import LensGaps from './LensGaps';
import LensPreview from './LensPreview';
import { filledClass, needsWords } from './lensModel';
import RealFile from './RealFile';

function Stat({ label, value, tone = '', of = null }) {
  return (
    <div className="bb-stat-card">
      <div className="bb-stat-label">{label}</div>
      <div className={`bb-stat-value ${tone}`}>
        {value}
        {of ? <span className="bnf-lens-of"> of {of}</span> : null}
      </div>
    </div>
  );
}

/*
 * One carrier format, checked on the Census tab (plan.md §8.12; K81–K88; old CensusFormatLens.jsx at 891f1b3): its
 * head with "⬇ Export" for each format it ships as and "Check the real file ▸" (K81, K82), the stats (K83), the gap
 * queue (K84), what it still needs, the warnings, column by column (K87), what we do not store (K88) and the first rows
 * exactly as the carrier receives them. Everything is the server's, from the builder the download runs.
 * "Make these required on this deal" is dropped (K86): the request's formats already make their columns required.
 * "⬇ Export" goes through the check before the download (K69, slice 46).
 */
export default function FormatLens({ dealId, format }) {
  const found = useRfpFormat(dealId, format.key);
  const files = useRfpDownload(dealId);
  const [checking, setChecking] = useState(false);
  if (found.isPending) return <Loading label={`Loading ${format.label}…`} />;
  if (found.isError) return <InlineError title={format.label} error={found.error} onRetry={() => found.refetch()} />;
  const detail = found.data;
  const carrier = detail.carrier || 'the carrier';
  const needs = needsWords(detail);
  return (
    <div className="bnf-lens">
      <div className="bb-panel bnf-lens-head" data-guide="census-lens-summary">
        <div className="bnf-lens-head-top">
          <div>
            <div className="bnf-export-name">
              {detail.label}
              {detail.file_formats.map((kind) => (
                <span key={kind} className="bnf-export-fmt bb-mono">
                  {kind.toUpperCase()}
                </span>
              ))}
            </div>
            <div className="bb-panel-sub">
              {carrier} · sheet “{detail.sheet}” · {detail.geometry} · one row per member · {detail.version}
            </div>
          </div>
          <div className="bnf-lens-actions">
            <span className="bnf-lens-downloads" data-guide="census-lens-download">
              {detail.file_formats.map((kind, index) => {
                const key = index === 0 ? detail.key : `${detail.key}-${kind}`;
                return (
                  <button
                    key={kind}
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={files.busy === key}
                    onClick={() => files.download(key, `${detail.carrier} census (${kind.toUpperCase()})`)}
                  >
                    {files.busy === key ? 'Building…' : `⬇ Export ${kind.toUpperCase()}`}
                  </button>
                );
              })}
            </span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              data-guide="census-lens-check"
              title="Build the real file and look inside it — including what only the fill knows"
              onClick={() => setChecking(true)}
            >
              Check the real file ▸
            </button>
          </div>
        </div>
        <div className="bb-stat-row bnf-lens-stats">
          <Stat label="Rows" value={detail.preview.total_rows} of={detail.max_rows} />
          <Stat label="Columns" value={detail.columns.length} />
          <Stat label="Filled" value={`${detail.filled_pct}%`} tone={filledClass(detail.filled_pct)} />
          <Stat label="We don't store" value={detail.gaps.length} />
          <Stat
            label="Warnings"
            value={detail.warnings.length}
            tone={detail.warnings.length ? 'bb-amber' : 'bb-green'}
          />
        </div>
        {detail.gap_items.length > 0 && (
          <div className="bnf-lens-gaps">
            <GapQueue key={detail.key} dealId={dealId} items={detail.gap_items} total={detail.gap_total} />
          </div>
        )}
        <div className="bnf-lens-ask">
          <div className="bnf-lens-ask-text">
            {needs ? (
              <>
                This format still needs <b>{needs}</b> for columns {carrier} requires.
              </>
            ) : (
              <>Every column {carrier} requires is filled on this deal.</>
            )}
          </div>
        </div>
      </div>

      <div className="bb-panel bnf-lens-section" data-guide="census-lens-warnings">
        <div className="bnf-lens-section-title">Warnings</div>
        {detail.warnings.length === 0 ? (
          <div className="bb-green">No warnings — this file builds clean.</div>
        ) : (
          detail.warnings.map((text) => (
            <div key={text} className="bnf-export-warning">
              ⚠ {text}
            </div>
          ))
        )}
        <div className="bnf-review-note">
          <i>Check the real file</i> adds what only the fill knows — a formula cell we refuse to overwrite.
        </div>
      </div>

      <LensColumns columns={detail.columns} />
      <LensGaps detail={detail} />
      <LensPreview carrier={carrier} preview={detail.preview} />
      {checking && <RealFile dealId={dealId} format={detail} onClose={() => setChecking(false)} />}
      {files.modal}
    </div>
  );
}
