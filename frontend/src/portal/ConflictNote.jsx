import { shownValue } from '../deal/shared/fieldValue';

/*
 * "Someone at your company changed this" (plan.md §8.20; L96). Ported from old Vantage 891f1b3 `ConflictNote`: the
 * page held an older value than the one now saved. Keep theirs drops ours; Use mine sends ours again against theirs.
 * A list answer (contacts, coverage) shows no value, only that it changed.
 */
export default function ConflictNote({ conflict, onKeep, onMine }) {
  if (!conflict) return null;
  const listed = Array.isArray(conflict.theirs) && conflict.theirs.some((item) => typeof item === 'object');
  return (
    <div className="bnf-portal-conflict" role="status">
      {listed ? (
        'Someone at your company changed this while you had this page open.'
      ) : (
        <>
          Someone at your company changed this to <b>{shownValue(conflict.theirs) || '(blank)'}</b> while you had this
          page open.
        </>
      )}{' '}
      <button type="button" className="bnf-linklike" onClick={onKeep}>
        Keep theirs
      </button>
      {' · '}
      <button type="button" className="bnf-linklike" onClick={onMine}>
        Use mine
      </button>
    </div>
  );
}
