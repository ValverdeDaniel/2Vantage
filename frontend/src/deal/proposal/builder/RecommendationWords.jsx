import { useState } from 'react';
import cx from '../../../ui/cx';
import { recommendationWords } from './builderModel';

/*
 * The foot of the Plans card (plan.md §5.4, §8.14; J52, J55, J56; the old `bnf-build-rec` at 891f1b3): the
 * recommendation's status ("2 of 3 current plans have a recommendation", "We recommend …"), each recommended plan with
 * its own option number and its own change against what it replaces (several picks for one current plan each show
 * theirs, §5.4), "Recommend the renewal for every plan", and "Why this, in your words", saved on blur
 * (`reasons.<line>`). The picks themselves are the pages' "Our recommendation" row.
 */
function Pick({ pick }) {
  const change = pick.change?.text;
  return (
    <div className="bb-drop-meta">
      {pick.option ? `Option ${pick.option} · ` : ''}
      {pick.keep ? `Keep ${pick.words}` : pick.words}
      {change ? ` · ${change}` : ''}
      {!pick.keep && pick.replacing.length ? ` · replacing ${pick.replacing.join(' + ')}` : ''}
    </div>
  );
}

export default function RecommendationWords({ line, busy, onRenewals, onReasons }) {
  const [draft, setDraft] = useState(null);
  const words = recommendationWords(line);
  const rec = line.recommendation;
  const saved = line.reasons ?? '';
  return (
    <div className="bnf-build-rec" data-guide="build-recommendation">
      <div className={cx('bnf-pp-rec-status', words.open && 'is-open')}>
        {words.tail ? (
          <>
            <b>{words.long}</b> {words.tail}
          </>
        ) : (
          words.long
        )}
        {rec.renewals.length > 0 && (
          <button
            type="button"
            className="btn btn-secondary btn-sm bnf-pp-renew-all"
            disabled={busy || rec.sold.length > 0}
            onClick={() => onRenewals(rec.renewals)}
          >
            Recommend the renewal for every plan
          </button>
        )}
      </div>
      {rec.plans.map((pick) => (
        <Pick key={pick.plan_id} pick={pick} />
      ))}
      <label className="bnf-build-rec-why">
        <span>Why this, in your words</span>
        <textarea
          rows={3}
          maxLength={4000}
          value={draft ?? saved}
          placeholder={`Why you are recommending this for ${line.label}. The client reads it under the recommendation.`}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={() => {
            if (draft !== null && draft.trim() !== saved) onReasons(draft.trim());
            setDraft(null);
          }}
        />
      </label>
    </div>
  );
}
