/*
 * The badge beside each intake answer (plan.md §3.7; B6), ported from old Vantage 891f1b3 `IntakeTab.jsx`
 * (`badgeFor`, `filledBadge`, D-124): its colour says how the answer stands, its word whose it is. Pure, over the
 * row the form builds: the stored answer, its `sources` entry and the server's status (`missing` or `to_check`, from
 * the one `needed` rule and `documents.review_rules.open_warning`), so the star, "Missing" and the counts agree (B6's
 * fix). "Verified ✓" is only ever a person: typed, entered for the client, the client's approved answer, or a person's
 * approval of what was read.
 */
import { isBlank } from '../shared/fieldValue';

const PERSON = new Set(['typed', 'relay', 'client']);
const GREEN = 'bb-badge-green';
const ROSE = 'bb-badge-rose';

const LOCATED = {
  found: 'printed in the file',
  derived: 'worked out from a printed figure',
  weak: 'a common figure, not pinned down',
  absent: 'not found in the file',
  nocheck: 'the file cannot say',
};

const PERSON_TITLE = {
  typed: '',
  relay: 'Entered for the client by a person',
  client: 'From the client — approved',
};

function readTitle(source) {
  const where = source.page ? ` (page ${source.page})` : '';
  const check = LOCATED[source.loc?.state];
  return [
    `Read by AI${where}; nobody has approved it yet`,
    source.low ? `The reader was unsure: ${source.low}` : '',
    check ? `File check: ${check}` : '',
  ]
    .filter(Boolean)
    .join('\n');
}

/** {label, className, title} for a row of the form. */
export function badgeFor(row) {
  if (isBlank(row.value)) {
    return row.status === 'missing'
      ? { label: 'Missing', className: ROSE, title: 'Needed on this deal' }
      : { label: '—', className: 'bb-badge-gray', title: '' };
  }
  const source = row.source || {};
  const mark = source.mark?.state;
  if (mark === 'check') return { label: '⚑ Needs checking', className: ROSE, title: 'Flagged for a second look' };
  if (row.status === 'to_check') return { label: 'Review', className: 'bb-badge-amber', title: readTitle(source) };
  if (mark === 'ignored') {
    return { label: 'Ignored', className: 'bb-badge-gray', title: 'Warning ignored — the value stays as read' };
  }
  if (source.confirmed) return { label: 'Verified ✓', className: GREEN, title: 'Approved by a person' };
  if (PERSON.has(source.origin)) return { label: 'Verified ✓', className: GREEN, title: PERSON_TITLE[source.origin] };
  if (source.origin === 'ai') return { label: 'Read by AI', className: GREEN, title: readTitle(source) };
  return { label: 'On file', className: GREEN, title: 'On file; where it came from was not recorded' };
}
