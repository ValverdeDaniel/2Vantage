import { useEffect, useMemo, useRef, useState } from 'react';
import ClientSpreadsheetButton from '../builder/ClientSpreadsheetButton';
import { publish } from '../../shared/viewerBridge';
import { builtWords } from './exportFiles';
import { tabModel } from './gridModel';
import usePreviewCopy from './usePreviewCopy';
import ViewerBar from './ViewerBar';
import WorkbookChecks from './WorkbookChecks';
import WorkbookGrid from './WorkbookGrid';
import WorkbookPages from './WorkbookPages';
import WorkbookTabs from './WorkbookTabs';
import { checkList, markMap, readMode, stepCell, writeMode } from './workbookModel';
import { workbookState } from './viewerState';
import { columnLetter } from './gridModel';

const FILE = 'workbook';
const storage = () => (typeof window === 'undefined' ? null : window.localStorage);

/*
 * The Export viewer's Excel view (plan.md §8.14; J107, J112, J116–J118; the old WorkbookViewer.jsx at 891f1b3): the
 * client spreadsheet as Excel will show it, before anyone downloads it. The server builds the download's own sheet
 * model, one tab a request, every value the one the file stores drawn through its number format
 * (proposals/viewer/workbook.py); this draws it. It opens on the tab Excel opens on and keeps to the tab picked
 * (`selected`, held by the Advisor so a view switch keeps it); Screen or Printed pages, kept per browser; the checks per
 * tab, each jumping to its cell; Ctrl+PgUp and Ctrl+PgDn between tabs and the arrows between cells, as in Excel.
 * The tab on screen is published for Work with Claude (J120). The root says what it is doing for the walks:
 * `data-render` loading | ready | error, `data-viewer-tab`.
 */
export default function WorkbookViewer({ dealId, chips, selected, onSelect }) {
  const [mode, setMode] = useState(() => readMode(storage()));
  const [cell, setCell] = useState(null); // {tab, r, c}
  const [scrollTo, setScrollTo] = useState(null);
  const rootRef = useRef(null);
  const copy = usePreviewCopy(dealId, { file: FILE, tab: selected || '', shown: true });
  const data = copy.data;
  const tabs = useMemo(() => data?.tabs || [], [data]);
  const wanted = selected && tabs.some((t) => t.title === selected) ? selected : data?.opens_on;
  const switching = Boolean(data?.tab) && data.tab.title !== wanted;
  const tab = switching ? null : data?.tab || null;
  const model = useMemo(() => tabModel(tab), [tab]);
  const checks = useMemo(() => checkList(tab), [tab]);
  const marks = useMemo(() => markMap(checks), [checks]);
  const picked = cell && tab && cell.tab === tab.title ? cell : null;
  const index = tabs.findIndex((t) => t.title === wanted);

  useEffect(() => {
    rootRef.current?.focus({ preventScroll: true });
  }, []);
  // Work with Claude is told the tab on screen (J120; slice 30).
  const told = useMemo(() => (tab ? workbookState(tab.title) : null), [tab]);
  useEffect(() => (told ? publish(dealId, told) : undefined), [dealId, told]);

  const pickMode = (next) => {
    setMode(next);
    writeMode(storage(), next);
  };
  const goTab = (title) => onSelect(title === data?.opens_on ? null : title);
  const goCell = (r, c) => {
    setCell({ tab: tab.title, r, c });
    setScrollTo({ r, c, at: Date.now() });
  };
  const goCheck = (check) => {
    if (mode !== 'screen') pickMode('screen');
    goCell(check.r, check.c);
  };
  const onKeyDown = (event) => {
    if (event.target.closest?.('input, textarea, select, [contenteditable="true"]')) return;
    if (event.ctrlKey && (event.key === 'PageDown' || event.key === 'PageUp')) {
      event.preventDefault();
      const next = tabs[index + (event.key === 'PageDown' ? 1 : -1)];
      if (next) goTab(next.title);
      return;
    }
    if (!picked || mode !== 'screen') return;
    const moved = stepCell(tab, picked, event.key);
    if (!moved) return;
    event.preventDefault();
    goCell(moved.r, moved.c);
  };

  let status = builtWords(data?.built_at, tabs.length, 'tab');
  if (copy.building) status = data ? 'Rebuilding…' : 'Building the spreadsheet…';
  else if (copy.stale) status = 'The deal changed since this copy';
  const renderState = copy.refused ? 'error' : tab ? 'ready' : 'loading';

  return (
    <div
      className="bnf-xv bnf-xw"
      data-render={renderState}
      data-viewer-tab={tab ? tab.title : undefined}
      ref={rootRef}
      tabIndex={-1}
      onKeyDown={onKeyDown}
    >
      <ViewerBar
        chips={chips}
        draft={data?.draft}
        status={status}
        building={copy.building}
        onRefresh={copy.refresh}
        download={
          <ClientSpreadsheetButton
            dealId={dealId}
            label="⬇ Download spreadsheet"
            title="The same file the builder downloads"
          />
        }
      >
        <span className="bnf-xw-mode" role="group" aria-label="How to look at it">
          {[
            ['screen', 'Screen', 'The tab as Excel shows it on screen'],
            ['pages', 'Printed pages', 'The tab on letter paper, page by page, as Excel prints it'],
          ].map(([key, label, hint]) => (
            <button
              key={key}
              type="button"
              className={`bnf-viewtab ${mode === key ? 'bnf-viewtab-on' : ''}`}
              aria-pressed={mode === key}
              onClick={() => pickMode(key)}
              title={hint}
            >
              {label}
            </button>
          ))}
        </span>
      </ViewerBar>

      {copy.failed && data && (
        <div className="bnf-xv-notice bnf-xv-notice-warn" role="status">
          {copy.failed} This is the last copy.{' '}
          <button type="button" className="bnf-refresh-retry" onClick={copy.refresh}>
            Try again
          </button>
        </div>
      )}
      {copy.refused && (
        <div className="bnf-xv-notice bnf-xv-notice-warn" role="alert">
          {copy.refused} The spreadsheet download says the same.
        </div>
      )}
      {!data && !copy.refused && (
        <div className="bnf-xv-notice">
          {copy.failed ? (
            <>
              {copy.failed}{' '}
              <button type="button" className="bnf-refresh-retry" onClick={copy.refresh}>
                Try again
              </button>
            </>
          ) : (
            'Building the spreadsheet as it will download…'
          )}
        </div>
      )}
      {switching && <div className="bnf-xv-notice">Building the {wanted} tab as it will download…</div>}

      {tab && (
        <>
          <WorkbookChecks key={`checks ${tab.title}`} tab={tab} checks={checks} onGo={goCheck} />
          {mode === 'screen' ? (
            <div className="bnf-xw-stage">
              <WorkbookGrid
                tab={tab}
                model={model}
                selected={picked}
                onSelect={goCell}
                marks={marks}
                scrollTo={scrollTo}
              />
            </div>
          ) : (
            <WorkbookPages key={`pages ${tab.title}`} tab={tab} model={model} />
          )}
        </>
      )}
      {data && tabs.length > 0 && (
        <WorkbookTabs tabs={tabs} current={wanted} opensOn={data.opens_on} onPick={goTab} />
      )}
      {tab && (
        <div className="bnf-xv-about">
          Every value is the one the download stores, and every number drawn through its format as Excel draws it.{' '}
          {picked ? `Cell ${columnLetter(picked.c)}${picked.r + 1} selected. ` : ''}
          Excel lays text out a pixel at a time, so text marked tight can sit differently on another screen; Ctrl+PgUp
          and Ctrl+PgDn move between tabs, as in Excel.
        </div>
      )}
    </div>
  );
}
