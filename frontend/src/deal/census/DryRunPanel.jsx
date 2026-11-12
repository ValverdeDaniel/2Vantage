import { useState } from 'react';
import Button from '../../ui/Button';
import { dryRunWords, fileWords, removesSomeone } from './mapping';

const GROUPS = [
  { key: 'added', title: 'Added' },
  { key: 'changed', title: 'Changed' },
  { key: 'removed', title: 'Removed' },
  { key: 'kept', title: 'Kept although the file no longer lists them' },
];

function who(person) {
  const role = person.kind === 'dependent' ? ' (dependent)' : '';
  if (person.columns) return `${person.name}${role}: ${person.columns.join(', ')}`;
  if (person.why) return `${person.name}${role}: ${person.why}`;
  return `${person.name}${role}${person.restored ? ', back on the roster' : ''}`;
}

/*
 * The dry run, before the roster changes (plan.md §5.3.2 step 8; C17): who would be added, changed (with the columns,
 * never the values), removed and kept, and nothing is written until Apply. Anyone removed is said out loud: removal
 * is soft, and a later file brings them back. Shown in the old reformat banner's frame (`bnf-reformat-*`).
 */
export default function DryRunPanel({ answer, onApply, onBack, applying }) {
  const [open, setOpen] = useState('');
  const counts = answer.counts;
  const masked = answer.masked_ssns || {};
  return (
    <div className={`bnf-reformat-banner ${removesSomeone(answer) ? 'bnf-reformat-attention' : 'bnf-reformat-done'}`}>
      <div className="bnf-reformat-title">Before anything changes</div>
      <div className="bnf-reformat-body">
        {fileWords(counts)} On the roster: <strong>{dryRunWords(counts)}</strong>.
      </div>
      {counts.removed > 0 && (
        <div className="bnf-reformat-body">
          {counts.removed} {counts.removed === 1 ? 'person' : 'people'} the file no longer lists will be removed.
          Removal is soft: a later file that lists them brings them back. People someone worked on are kept.
        </div>
      )}
      {masked.unmatched > 0 && (
        <div className="bnf-reformat-body">
          {masked.unmatched} SSN{masked.unmatched === 1 ? '' : 's'} in the file showed only the last four and matched
          nobody on file — left blank.
        </div>
      )}
      {GROUPS.filter((group) => answer[group.key].length > 0).map((group) => (
        <div className="bnf-reformat-body" key={group.key}>
          <button
            type="button"
            className="bnf-reformat-link"
            onClick={() => setOpen((shown) => (shown === group.key ? '' : group.key))}
          >
            {open === group.key ? 'Hide' : 'Show'} {group.title.toLowerCase()} ({answer[group.key].length})
          </button>
          {open === group.key && (
            <ul className="bnf-reformat-list">
              {answer[group.key].map((person, index) => (
                <li key={person.id ?? `new-${index}`}>{who(person)}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <div className="bb-toolbar-actions">
        <Button size="sm" onClick={onBack} disabled={applying}>
          Back to the mapping
        </Button>
        <Button variant="primary" size="sm" onClick={onApply} busy={applying}>
          {applying ? 'Applying…' : 'Apply to the roster ▸'}
        </Button>
      </div>
    </div>
  );
}
