import { useMemo } from 'react';
import { useIntake } from '../../api/intake';
import cx from '../../ui/cx';
import InlineError from '../../ui/InlineError';
import { badgeFor, buildSections } from '../intake';
import { isBlank, shownValue } from '../shared/fieldValue';

/*
 * An intake file's Scanned data (plan.md §8.16; E44, D130; the old DocumentsTab's intake view, D-209; slice 65): the
 * whole intake form, card by card as the Intake tab lays it out, so what was read from this file sits among the
 * questions around it. Questions this file answered carry their badge (intake's `badgeFor`) and open where the file
 * prints them (↗ in the file: `intake:<key>`); the rest are muted, with "Other file" when another file gave the
 * answer. A question this file answered always shows, even one the form now hides. Contacts and the current coverage
 * follow read-only: they keep no page in the file, and the Intake tab changes them.
 */
const words = (text) =>
  String(text || '')
    .replace(/_/g, ' ')
    .replace(/^./, (c) => c.toUpperCase());

function rowsOf(sections, fromFile) {
  return sections.flatMap((section) =>
    section.rows
      .filter((row) => row.visible || fromFile(row))
      .map((row, i) => ({ ...row, band: i === 0 ? section.label : '', mine: fromFile(row) })),
  );
}

function Known({ intake }) {
  const lines = (intake.coverage || []).filter((row) => row.in_force !== false);
  const contacts = intake.contacts || [];
  return (
    <div className="bnf-scan-side bb-mt">
      <div className="bnf-scan-section-head">Contacts</div>
      {contacts.length ? (
        contacts.map((c) => (
          <div key={`ct-${c.id}`} className="bnf-scan-field bnf-scan-field-static">
            <span className="bnf-scan-field-label">{c.role_label || words(c.role)}</span>
            <span className="bnf-scan-field-value">
              {[c.name, c.title, c.email, c.phone].filter(Boolean).join(' · ') || '—'}
            </span>
            <span />
          </div>
        ))
      ) : (
        <div className="bnf-scan-field-none">No contacts on the deal yet.</div>
      )}
      <div className="bnf-scan-section-head">Current coverage</div>
      {lines.length ? (
        lines.map((row) => (
          <div key={`cl-${row.id}`} className="bnf-scan-field bnf-scan-field-static">
            <span className="bnf-scan-field-label">{row.label}</span>
            <span className="bnf-scan-field-value">
              {[row.from_plans?.carrier || row.carrier, words(row.from_plans?.funding || row.funding)]
                .filter(Boolean)
                .join(' · ') || '—'}
            </span>
            <span />
          </div>
        ))
      ) : (
        <div className="bnf-scan-field-none">No current coverage on the deal yet.</div>
      )}
      <div className="bnf-scan-field-none">
        Contacts and coverage keep no page in the file, so they cannot be found in it; change them on the Intake tab.
      </div>
    </div>
  );
}

export default function IntakeFileView({ deal, meta, scope, activeRef, onShow }) {
  const intake = useIntake(deal.id);
  const ids = useMemo(() => new Set(scope.ids), [scope.ids]);
  const rows = useMemo(() => {
    if (!intake.data) return [];
    return rowsOf(buildSections(meta.intake?.form, intake.data), (row) => ids.has(row.source?.doc));
  }, [intake.data, meta.intake, ids]);
  if (intake.isPending) return <div className="bb-subtitle bb-mt">Loading the intake form…</div>;
  if (intake.isError) {
    return <InlineError compact title="Could not load the intake form." error={intake.error} onRetry={() => intake.refetch()} />;
  }
  const read = rows.filter((row) => row.mine).length;
  const open = (row) => row.source?.doc && onShow(row.source.doc, `intake:${row.key}`);
  return (
    <>
      <div className="bnf-scan-form-note bb-mt">
        {read
          ? `${read} of ${rows.length} questions read from this file; the rest of the intake form is shown muted.`
          : 'Nothing on the intake form was read from this file yet: the whole form is shown so you can see what it asks.'}
      </div>
      <div className="bnf-scan-form bb-mt" role="list" aria-label="The intake form">
        {rows.map((row) => {
          const badge = row.mine ? badgeFor(row) : row.source?.doc ? { label: 'Other file', className: 'bb-badge-gray' } : null;
          const opens = Boolean(row.source?.doc);
          return [
            row.band && (
              <div key={`band-${row.key}`} className="bnf-scan-section-head">
                {row.band}
              </div>
            ),
            <div
              key={row.key}
              role="listitem"
              tabIndex={opens ? 0 : undefined}
              data-intake-key={row.key}
              title={!row.mine && opens ? 'Read from another file: open it there' : badge?.title || undefined}
              className={cx(
                'bnf-scan-field',
                !row.mine && 'bnf-scan-field-other',
                activeRef === `intake:${row.key}` && 'bb-active',
              )}
              onClick={() => open(row)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  open(row);
                }
              }}
            >
              <span className="bnf-scan-field-label">{row.question.label}</span>
              <span className="bnf-scan-field-value">{isBlank(row.value) ? '—' : shownValue(row.value)}</span>
              {badge ? <span className={`bb-badge ${badge.className}`}>{badge.label}</span> : <span />}
            </div>,
          ];
        })}
      </div>
      <Known intake={intake.data} />
    </>
  );
}
