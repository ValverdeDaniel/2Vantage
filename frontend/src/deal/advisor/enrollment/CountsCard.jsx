import { useState } from 'react';
import { formErrorText } from '../../../lib/errors';
import CensusNames from './CensusNames';
import CensusNotice from './CensusNotice';
import CountsTable from './CountsTable';
import * as cm from './countsModel';

/*
 * Summary tiers, the counts card above the board (plan.md §5.5, §8.14; F85, F88, F90–F92; the old PlanCountsCard,
 * `bnf-pv-composer bnf-pc-card`): the line's one switch, plan chips with All / None, a row of counts per picked plan
 * (inputs follow the rate basis) and, where the line has no current plan or a figure is stored, the whole-line row.
 * With two current plans it opens on the split: the current plans picked, the line figure as their placeholder. The
 * census notice (F91) and the census plan names (F90) sit inside. Save writes the line's whole typed set; the switch
 * saves at once once counts are typed. Priced versions are not offered: they price their plan's people.
 */
export default function CountsCard({ block, plans, labels, lineLabel, preselect, kit, onClose }) {
  const keys = block.keys;
  const offered = cm.candidates(plans);
  const currents = plans.filter((plan) => plan.role === 'current');
  const split = block.split;
  const [picked, setPicked] = useState(() =>
    cm.initialPicked(offered, preselect ?? (split ? currents.map((plan) => plan.id) : [])),
  );
  const [rows, setRows] = useState(() => cm.initialRows(offered, keys));
  const [figure, setFigure] = useState(() => cm.blankRow(keys, block.figure));
  const [choice, setChoice] = useState(() => cm.initialChoice(block.texts));
  const [on, setOn] = useState(block.on);
  const typed = block.typed_plans + (block.figure ? 1 : 0) > 0;
  const chosen = offered.filter((plan) => picked.includes(plan.id));
  const problems = chosen.map((plan) => cm.rowProblem(rows[plan.id] ?? {}, keys)).filter(Boolean);
  const figureProblem = block.offers_figure && cm.badKeys(figure, keys).length > 0;
  const what = keys.length > 1 ? 'tiers' : keys[0];

  const toggle = (id) => setPicked((now) => (now.includes(id) ? now.filter((x) => x !== id) : [...now, id]));
  const setCount = (id, key, value) => setRows((now) => ({ ...now, [id]: { ...now[id], [key]: value } }));
  const copyFirst = () =>
    setRows((now) => ({ ...now, ...Object.fromEntries(chosen.slice(1).map((p) => [p.id, { ...now[chosen[0].id] }])) }));
  const renewalNote = (plan) => {
    const renewals = offered.filter((other) => other.renews_id === plan.id && !picked.includes(other.id));
    if (!renewals.length) return '';
    return renewals.length === 1 ? 'Its renewal uses these too.' : `Its ${renewals.length} renewals use these too.`;
  };

  function flip() {
    const next = !on;
    if (!typed) return setOn(next); // before anything is typed the switch is only the first save's setting
    return kit.flip(next).then(() => setOn(next), () => {});
  }

  function save() {
    const body = cm.bodyFor({ keys, picked: chosen.map((p) => p.id), rows, figure, offersFigure: block.offers_figure, on });
    const names = cm.namesBody(block.texts, currents, choice);
    if (names) body.census_names = names;
    const n = chosen.length;
    const words = n
      ? `Counts saved for ${n} plan${n === 1 ? '' : 's'}${on ? '' : ' (switch off)'}`
      : 'Typed counts saved for the whole line';
    kit.save(body, words).then(onClose, () => {});
  }

  return (
    <div className="bnf-pv-composer bnf-pc-card" role="region" aria-label={`Summary ${lineLabel.toLowerCase()} ${what}`}>
      <div className="bnf-pv-head">
        <span className="bnf-pv-title">
          Summary {lineLabel.toLowerCase()} {what}
        </span>
        <span className="bnf-pv-sub">
          Type how many employees each plan covers. While on, these counts price the plans you pick and the quotes that
          replace them; a census imported later takes over until you keep them.
        </span>
        <button type="button" className="bnf-pv-inline-btn bnf-conc-remove" title="Close without saving" onClick={onClose}>
          ✕
        </button>
      </div>
      <CensusNotice block={block} plans={plans} busy={kit.busy} onKeep={kit.keep} />
      <label className="bnf-pc-switch">
        <input type="checkbox" role="switch" checked={on} aria-checked={on} disabled={kit.busy} onChange={flip} />
        <span>
          {on ? 'On — the plans below price on these counts' : 'Off — every plan prices on the census; your counts are kept'}
        </span>
      </label>
      <div className="bnf-pv-planpick">
        <span className="bnf-pv-picklabel">Plans ({picked.length || 'none'}):</span>
        {offered.map((plan) => (
          <button
            key={plan.id}
            type="button"
            className={`bnf-pv-chip ${picked.includes(plan.id) ? 'bnf-pv-chip-on' : ''}`}
            onClick={() => toggle(plan.id)}
          >
            {picked.includes(plan.id) ? '✓ ' : ''}
            {plan.carrier} · {plan.name}
            {plan.role === 'current' ? ' (current)' : ''}
          </button>
        ))}
        <span className="bnf-pv-quick">
          <button type="button" className="bnf-pv-quickbtn" onClick={() => setPicked(offered.map((p) => p.id))}>
            All
          </button>
          <button type="button" className="bnf-pv-quickbtn" onClick={() => setPicked([])}>
            None
          </button>
        </span>
      </div>
      {split?.figure && (
        <p className="bnf-pc-empty">
          Split {cm.countsText(split.figure, keys)} between the current plans: the line has {currents.length} now, so
          its figure no longer prices them.
        </p>
      )}
      {chosen.length || block.offers_figure ? (
        <CountsTable
          keys={keys}
          labels={labels}
          plans={chosen}
          rows={rows}
          onCount={setCount}
          figure={block.offers_figure ? figure : null}
          onFigure={(key, value) => setFigure((now) => ({ ...now, [key]: value }))}
          note={renewalNote}
          split={split?.figure}
        />
      ) : (
        <p className="bnf-pc-empty">
          {typed ? 'No plans picked: saving clears every typed count.' : 'Pick the plans to type counts for.'}
        </p>
      )}
      {block.texts?.length > 0 && currents.length > 0 && (
        <CensusNames texts={block.texts} currents={currents} choice={choice} onChoose={(text, id) => setChoice((now) => ({ ...now, [text]: id }))} />
      )}
      {(problems.length > 0 || figureProblem) && (
        <p className="bnf-pc-error" role="alert">
          {problems[0] || 'Counts are whole numbers of people.'} Each picked plan needs at least one person.
        </p>
      )}
      {kit.error && (
        <p className="bnf-pc-error" role="alert">
          {formErrorText(kit.error)}
        </p>
      )}
      <div className="bnf-pv-footer">
        <span className="bnf-pc-basis">{cm.basisText(block, lineLabel)}</span>
        <span className="bnf-pv-actions">
          <button type="button" className="btn btn-secondary btn-sm" disabled={chosen.length < 2} onClick={copyFirst}>
            Copy first row to all
          </button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={kit.busy || problems.length > 0 || figureProblem}
            onClick={save}
          >
            {kit.busy ? 'Saving…' : 'Save counts'}
          </button>
        </span>
      </div>
    </div>
  );
}
