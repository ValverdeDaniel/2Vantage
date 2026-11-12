import SourcePin from '../../viewer/SourcePin';
import FieldInput from '../shared/FieldInput';
import { isBlank, shownValue } from '../shared/fieldValue';
import { badgeFor } from './badges';
import { selectable } from './formModel';

/*
 * One question of the intake form (plan.md §8.9; B3, B4, B6–B8), in the old row's markup (891f1b3 `IntakeTab.jsx`
 * `fieldRow`, `bb-account-row bnf-intake-row`): the label with the rose star when this deal needs it, the answer (a
 * click opens its editor; ↗ opens the file it was read from), the badge, then the inline checks and a refused save's
 * sentence. Hidden questions are not drawn. The question's help is its title. While ☑ Select fields is on (B10), a
 * row is a tick box instead; an answer with nothing to review is locked.
 */
export default function QuestionRow(props) {
  const { row, editing, draft, error, onOpen, onKeyDown, onChange, onBlur, onDone, select } = props;
  if (!row.visible) return null;
  const { question } = row;
  const badge = badgeFor(row);
  const blank = isBlank(row.value);
  if (select) {
    const can = selectable(row);
    return (
      <div
        className={`bb-account-row bnf-intake-row bnf-row-selectable ${select.picked ? 'bnf-row-selected' : ''} ${can ? '' : 'bnf-row-locked'}`}
        onClick={() => can && select.onToggle()}
      >
        <input
          type="checkbox"
          className="bnf-select-check"
          checked={select.picked}
          disabled={!can}
          readOnly
          aria-label={question.label}
        />
        <div className="bb-account-label">
          {question.label}
          {row.needed && <span className="bnf-qb-star">*</span>}
        </div>
        <div className={`bb-account-value ${blank ? 'bb-empty' : ''}`}>{blank ? '—' : shownValue(row.value)}</div>
        <span className={`bb-badge ${badge.className}`} title={badge.title || undefined}>
          {badge.label}
        </span>
      </div>
    );
  }
  const doc = row.source?.doc;
  return (
    <div className="bb-account-row bnf-intake-row" data-intake-field={row.key}>
      <div className="bb-account-label" title={question.help || undefined}>
        {question.label}
        {row.needed && (
          <span className="bnf-qb-star" title="Needed on this deal">
            *
          </span>
        )}
      </div>
      {editing ? (
        <div
          className="bnf-intake-editor"
          onKeyDown={onKeyDown}
          // A chip or Done click keeps the focus where it was, so Enter and Tab still go on from here.
          onMouseDown={question.type === 'multi' ? (event) => event.target.closest('.bnf-chip') && event.preventDefault() : undefined}
        >
          <FieldInput question={question} value={draft} onChange={onChange} onBlur={onBlur} autoFocus />
          {question.type === 'multi' && (
            <button type="button" className="btn btn-primary btn-sm" onClick={onDone}>
              Done
            </button>
          )}
        </div>
      ) : (
        <div
          className={`bb-account-value ${blank ? 'bb-empty' : ''}${doc ? ' bnf-has-src' : ''}`}
          onClick={onOpen}
          role="button"
          aria-label={`Edit ${question.label}`}
          title="Click to edit"
        >
          {blank ? '—' : shownValue(row.value)}
          {doc && <SourcePin docId={doc} valueRef={`intake:${row.key}`} />}
        </div>
      )}
      <span className={`bb-badge ${badge.className}`} title={badge.title || undefined}>
        {badge.label}
      </span>
      {(row.issues.length > 0 || error) && (
        <div className="bnf-issue-line">
          {error && (
            <span className="bb-rose" role="alert">
              {error}
            </span>
          )}
          {row.issues.map((issue) => (
            <span key={issue.code} className={issue.severity === 'error' ? 'bb-rose' : 'bb-amber'}>
              {issue.message}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
