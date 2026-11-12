import { useState } from 'react';
import { dryRun, useApplyImport, useDiscardImport, useUpdateImport } from '../../api/census';
import { errorText } from '../../lib/errors';
import Button from '../../ui/Button';
import Select from '../../ui/Select';
import { useToast } from '../../ui/useToast';
import DryRunPanel from './DryRunPanel';
import ReformatBanner from './ReformatBanner';
import RowChoices from './RowChoices';
import { badge, chooseField, fieldOptions, mappedCount, mappingChanges } from './mapping';

/*
 * Map census columns (plan.md §5.3.2, §8.10; C14–C17). Ported from old Vantage 891f1b3 `MappingReview.jsx`: it takes
 * over the tab while a mapping waits; every column shows up to three samples (read from the file for this screen,
 * never stored), its proposed census column and a Mapped / Check n% / Unmapped badge; picking a census column takes
 * it from the column that had it (C15; the old select greyed it out instead, so a taken column could not be moved). 2Vantage adds where the people are (sheet, header row, first person's row) and the dry run:
 * Apply first lists who is added, changed, removed and kept, and writes nothing until "Apply to the roster".
 */
export default function MappingDialog({ dealId, imp, meta, hasRoster, onClose }) {
  const toast = useToast();
  const [base, setBase] = useState(imp.mapping);
  const [mapping, setMapping] = useState(imp.mapping);
  const [answer, setAnswer] = useState(null);
  const [checking, setChecking] = useState(false);
  const update = useUpdateImport(dealId, imp.id);
  const apply = useApplyImport(dealId, imp.id);
  const discard = useDiscardImport(dealId, imp.id);
  if (base !== imp.mapping) {
    setBase(imp.mapping); // the server proposed again (a new sheet or header row): start from its mapping
    setMapping(imp.mapping);
    setAnswer(null);
  }
  const options = fieldOptions(meta);
  const used = new Set(mapping.map((entry) => entry.field).filter(Boolean));
  const busy = update.isPending || checking || apply.isPending;

  function fail(error) {
    toast.error(errorText(error));
  }

  function choose(changes) {
    setAnswer(null);
    update.mutate(changes, { onError: fail });
  }

  async function check() {
    setChecking(true);
    try {
      const changes = mappingChanges(imp.mapping, mapping);
      if (changes.length) await update.mutateAsync({ mapping: changes });
      setAnswer(await dryRun(imp.id));
    } catch (error) {
      fail(error);
    } finally {
      setChecking(false);
    }
  }

  function applyNow() {
    apply.mutate(undefined, {
      onSuccess: () => {
        toast.success('Mapping applied — census normalized');
        onClose();
      },
      onError: fail,
    });
  }

  return (
    <div className="bb-tab-page">
      <div className="bb-sov-header">
        <div>
          <div className="bb-tab-title">Map census columns</div>
          <div className="bb-subtitle">
            {imp.document_name}
            {imp.sheet_name ? ` · sheet "${imp.sheet_name}"` : ''} · header on row {imp.header_row} ·{' '}
            {mappedCount(mapping)} of {mapping.length} columns mapped
          </div>
        </div>
        <div className="bb-toolbar-actions">
          {hasRoster && (
            <Button size="sm" onClick={onClose} disabled={busy}>
              Close
            </Button>
          )}
          <Button
            size="sm"
            onClick={() => discard.mutate(undefined, { onSuccess: onClose, onError: fail })}
            busy={discard.isPending}
          >
            Discard this file
          </Button>
          <Button variant="primary" size="sm" onClick={check} busy={busy} disabled={Boolean(answer)}>
            {checking ? 'Checking…' : 'Apply mapping & build roster ▸'}
          </Button>
        </div>
      </div>

      {answer && (
        <DryRunPanel answer={answer} onApply={applyNow} onBack={() => setAnswer(null)} applying={apply.isPending} />
      )}
      <ReformatBanner imp={imp} busy={update.isPending} onUseOriginal={() => choose({ reformat: false })} />
      <RowChoices imp={imp} busy={busy} onChange={choose} />

      <div className="bb-panel">
        <div className="bnf-map-head">
          <div>Source column</div>
          <div>Sample values</div>
          <div>Canonical field</div>
          <div />
        </div>
        {mapping.map((entry) => {
          const shown = badge(entry);
          const samples = imp.mapping.find((item) => item.column === entry.column)?.samples || [];
          return (
            <div key={entry.column} className={`bnf-map-row ${entry.low ? 'bnf-map-low' : ''}`}>
              <div className="bnf-map-source">
                {entry.header || <i>(unnamed{entry.letter ? ` · column ${entry.letter}` : ''})</i>}
              </div>
              <div className="bnf-map-samples bb-mono">{samples.slice(0, 3).join(' · ') || '—'}</div>
              <div>
                <Select
                  aria-label={`Census column for ${entry.header || `column ${entry.letter}`}`}
                  value={entry.field || ''}
                  disabled={busy}
                  placeholder="— don't import —"
                  onChange={(event) => {
                    setAnswer(null);
                    setMapping((current) => chooseField(current, entry.column, event.target.value));
                  }}
                  options={options.map((option) => ({
                    ...option,
                    label:
                      used.has(option.value) && entry.field !== option.value
                        ? `${option.label} (in use)`
                        : option.label,
                  }))}
                />
              </div>
              <div>
                <span className={`bb-badge ${shown.className}`}>{shown.label}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="bb-dev-notice">
        <span className="bb-dev-icon">⚠</span>
        <div>
          Applying matches this file&apos;s people to the roster: values that came from a file move, what a person typed
          stays, and you see who is added, changed, removed and kept before anything changes. Columns marked
          <b> Check</b> were mapped with low confidence — the imported values will be flagged for review in the grid.
        </div>
      </div>
    </div>
  );
}
