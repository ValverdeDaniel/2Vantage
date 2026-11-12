import { useMemo, useRef, useState } from 'react';
import { useStar } from '../../../api/quotesBoard';
import { stopLossWorkbookUrl, useStopLoss } from '../../../api/stopLoss';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import { useToast } from '../../../ui/useToast';
import SavedBar from '../board/SavedBar';
import InForceCards from './InForceCards';
import LaserWhatIf from './LaserWhatIf';
import OptionTable from './OptionTable';
import StopLossControls from './StopLossControls';
import { boardColumns, fieldsByKey, settingsFrom, toggleLaser, withoutParam } from './stopLossModel';
import VerdictCards from './VerdictCards';

/*
 * The Advisor's Stop-loss analysis (plan.md §8.14; F98–F107, F29; the old close/StopLossAnalysis.jsx at 891f1b3):
 * reinsurance read as a contract, not a plan design. The basis names its source (F98); ① the contract in force, ② the
 * verdict ranked lowest first (F100, F101), the controls (F102), ③ the option table (F103), ④ the laser detail and its
 * what-if (F104), and ⤓ Export workbook, the five tabs (J166). The four controls are the saved settings (F29), on the
 * old saved bar, shown once the line has a plan. Nothing here computes money: every figure is the server's (rule 5).
 * The what-if lives only while the board is on screen; it is a parameter of the read, never stored.
 */
const TABS_HINT =
  'Five tabs, generated from this deal: In-Force Snapshot · Option Comparison · Binding Notes · Glossary · FIE Rates';

function Basis({ basis }) {
  if (basis.lives == null) return 'No enrolled headcount on this deal yet — every annual figure stays blank.';
  return (
    <>
      <b className="bb-mono">{basis.lives}</b> enrolled employees × <b className="bb-mono">{basis.months}</b> months ·
      every annual figure is PEPM × {basis.lives} × {basis.months} · {basis.words}
    </>
  );
}

export default function StopLossBoard({ dealId, meta, onOpenLine, onGoTab }) {
  const toast = useToast();
  const vocab = meta.stop_loss;
  const fields = useMemo(() => fieldsByKey(meta), [meta]);
  const [controls, setControls] = useState(() => settingsFrom(vocab.settings));
  const [dropped, setDropped] = useState({});
  const analysis = useStopLoss(dealId, withoutParam(dropped));
  const star = useStar(dealId);
  const [busy, setBusy] = useState(false);
  const working = useRef(false);
  const lineLabel = meta.lines.find((line) => line.key === vocab.line)?.label ?? vocab.line;

  if (analysis.isPending) return <Loading label="Loading the stop-loss analysis…" />;
  if (analysis.isError && !analysis.data) {
    return <InlineError title="Stop-loss analysis" error={analysis.error} onRetry={() => analysis.refetch()} />;
  }
  const data = analysis.data;
  const { currents, options, columns, best } = boardColumns(data, controls.rank_by, controls.hide_unscored);
  const rankLabel = vocab.rank_keys.find((key) => key.key === controls.rank_by)?.label ?? '';

  async function exportWorkbook() {
    if (working.current) return;
    working.current = true;
    setBusy(true);
    try {
      await downloadFile(stopLossWorkbookUrl(dealId), {
        fallbackName: 'stop-loss-analysis.xlsx',
      });
      toast.success('Stop-loss analysis workbook downloaded');
    } catch (error) {
      toast.error(
        errorText(error, {
          fallback: 'Could not build the stop-loss workbook',
        }),
      );
    } finally {
      working.current = false;
      setBusy(false);
    }
  }

  const onStar = (column) =>
    star.mutate(
      { planIds: [column.id], starred: !column.starred },
      { onError: (error) => toast.error(errorText(error)) },
    );

  if (!data.columns.length) {
    return (
      <div className="bnf-advisor-tab-split">
        <div className="bnf-sl-board">
          <div className="bb-panel">
            <div className="bb-panel-title">No stop-loss contract on this deal yet</div>
            <div className="bb-panel-sub">
              This group is marketing stop-loss, but nothing has been entered. Add the in-force contract and the
              incoming options on the {lineLabel} line of the Quote comparison, and the analysis fills in.
            </div>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => onOpenLine(vocab.line)}>
              Go to the {lineLabel} line ▸
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <SavedBar
        view={vocab.view}
        line={vocab.line}
        lineLabel={lineLabel}
        current={controls}
        onApply={(config) => setControls(settingsFrom(vocab.settings, config))}
      />
      <div className="bnf-advisor-tab-split">
        <div className="bnf-sl-board">
          <div className="bnf-sl-head">
            <div>
              <div className="bb-tab-title">Stop-loss analysis</div>
              <div className="bnf-sl-basis">
                <Basis basis={data.basis} />
              </div>
              <div className="bb-subtitle">
                Compare laser liability and maximum annual liability — never premium alone.
              </div>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy || Boolean(data.refusal)}
              onClick={exportWorkbook}
              title={data.refusal || TABS_HINT}
            >
              {busy ? 'Building…' : '⤓ Export workbook'}
            </button>
          </div>
          {data.basis.lives == null && (
            <div className="bnf-sl-warn">
              No enrolled employees on this deal yet, so every PEPM-driven annual figure below is blank. Type the
              medical counts on the Quote comparison, or add the roster on the Census tab.
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => onGoTab('census')}>
                Census ▸
              </button>
            </div>
          )}
          <InForceCards currents={currents} fields={fields} terms={vocab.terms} />
          <VerdictCards
            options={options}
            currents={currents}
            single={data.current_id != null}
            rankLabel={rankLabel}
            punchline={data.punchline}
            onStar={onStar}
          />
          <StopLossControls
            rankKeys={vocab.rank_keys}
            controls={controls}
            onControls={setControls}
            whatIf={Object.keys(dropped).length > 0}
            onReset={() => setDropped({})}
          />
          <OptionTable columns={columns} best={best} controls={controls} fields={fields} terms={vocab.terms} />
          <LaserWhatIf
            columns={columns}
            dropped={dropped}
            onToggle={(planId, n) => setDropped((now) => toggleLaser(now, planId, n))}
          />
        </div>
      </div>
    </>
  );
}
