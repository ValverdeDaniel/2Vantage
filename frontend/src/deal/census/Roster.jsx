import { useMemo, useRef, useState } from 'react';
import { useStartImport } from '../../api/census';
import EditModePrompt from '../../grid/EditModePrompt';
import { errorText } from '../../lib/errors';
import ConfirmDialog from '../../ui/ConfirmDialog';
import { useToast } from '../../ui/useToast';
import ReviewBulkBar from '../../valuereview/ReviewBulkBar';
import CensusCounts from './CensusCounts';
import CobraCheck from './CobraCheck';
import ImportDoor from './ImportDoor';
import { lastApplied } from './mapping';
import { LineChips, Pager, SelectBar } from './RosterBars';
import RosterGrid from './RosterGrid';
import RosterToolbar from './RosterToolbar';
import { chipGroups, defaultHidden, filledRefs, hintRoom, shownFields } from './rosterModel';
import useFittedColumns from './useFittedColumns';
import useRosterActions from './useRosterActions';
import useRosterGrid from './useRosterGrid';
import useRosterWrites from './useRosterWrites';

/*
 * The Roster (plan.md §8.10; C1–C10, C25; the old CensusGrid at 891f1b3, its order and words): under the header, its
 * counts and banners (CensusTab), the COBRA tick (intake's, C25), the toolbar, the ☑ Select cells bar or the review
 * bar, the line chips, the grid, the pager by employee, then the import door and the counts the pricing reads. ✎ Edit
 * is a screen mode (C4): "These came from the client" and the undo stack live only while it is on.
 */
export default function Roster({ deal, meta, census, onPage, onReview, refetch }) {
  const toast = useToast();
  const remap = useStartImport(deal.id);
  const [editing, setEditing] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [relay, setRelay] = useState(false);
  const [picking, setPicking] = useState(false);
  const [picked, setPicked] = useState(() => new Set());
  const [hidden, setHidden] = useState(null); // null: the default (C2)
  const [confirmClear, setConfirmClear] = useState(false);
  const scrollRef = useRef(null);

  const { summary } = census;
  const groups = chipGroups(meta.census);
  const shownHidden = useMemo(() => hidden ?? defaultHidden(meta.census, census.columns), [hidden, meta, census]);
  const fields = useFittedColumns(
    useMemo(() => shownFields(meta.census, shownHidden), [meta, shownHidden]),
    hintRoom,
  );
  const relationships = meta.census.fields.find((field) => field.key === 'relationship')?.choices || [];

  const writes = useRosterWrites(deal.id, editing, { relay });
  const enter = () => {
    setPicking(false);
    setPicked(new Set());
    setEditing(true);
    return true;
  };
  const { grid, prompt, landOn } = useRosterGrid({
    members: census.members,
    fields,
    editing,
    writes,
    enterEdit: enter,
    scrollRef,
  });
  const actions = useRosterActions({ dealId: deal.id, writes, relay, landOn, onPage, pageSize: census.page.page_size });

  const done = async () => {
    setLeaving(true);
    try {
      await writes.settle();
    } finally {
      setLeaving(false);
      setEditing(false);
      setRelay(false); // never inherited by a later visit (D-060)
    }
  };
  const stopPicking = () => {
    setPicking(false);
    setPicked(new Set());
  };
  const togglePick = (ref) =>
    setPicked((now) => {
      const next = new Set(now);
      if (next.has(ref)) next.delete(ref);
      else next.add(ref);
      return next;
    });
  const applied = lastApplied(census.imports);
  const remapFile = () =>
    remap.mutate(
      { documentId: applied.document_id },
      { onSuccess: (imp) => onReview(imp.id), onError: (error) => toast.error(errorText(error)) },
    );
  const markPicked = async (action) => {
    const refs = filledRefs(census, picked);
    if (await actions.mark(action, refs, 'the selected cells')) stopPicking();
  };

  const ui = { editing, picking, picked, onPick: togglePick, grid, prompt, errorOf: writes.errorOf };
  const toolbarActions = {
    addEmployee: actions.addEmployee,
    askClear: () => setConfirmClear(true),
    remap: applied ? remapFile : null,
    template: actions.template,
    exportCensus: actions.exportCensus,
    startPicking: () => setPicking(true),
    stopPicking,
    selectMissing: async () => {
      const refs = await actions.missing();
      if (refs) setPicked(new Set(refs));
    },
  };
  const edit = { enter, relay, setRelay, undo: grid.undo, canUndo: writes.canUndo, done, leaving };
  const review = census.review || {};

  return (
    <>
      <CobraCheck dealId={deal.id} cobra={census.cobra} onChanged={refetch} />
      <RosterToolbar
        mode={{ editing, picking }}
        edit={edit}
        actions={toolbarActions}
        busy={{ ...actions.busy, remap: remap.isPending }}
      />
      {picking && (
        <SelectBar
          count={picked.size}
          filled={filledRefs(census, picked).length}
          busy={actions.busy.mark}
          onMark={markPicked}
        />
      )}
      {!picking && review.open > 0 && (
        <ReviewBulkBar
          counts={review}
          target="the whole roster"
          busy={actions.busy.mark ? 'approve' : ''}
          onAction={(action) => actions.mark(action, null, 'the roster')}
        />
      )}
      <LineChips
        groups={groups}
        hidden={shownHidden}
        onToggle={(key) =>
          setHidden(() => {
            const next = new Set(shownHidden);
            if (next.has(key)) next.delete(key);
            else next.add(key);
            return next;
          })
        }
      />
      <RosterGrid
        members={census.members}
        fields={fields}
        ui={ui}
        relationships={relationships}
        onAddDependent={actions.addDependent}
        onRemove={actions.remove}
        onAddEmployee={actions.addEmployee}
      />
      <Pager page={census.page} onPage={onPage} />
      <ImportDoor
        dealId={deal.id}
        meta={meta}
        onStarted={(imp) => onReview(imp.id)}
        label="Import another census file ▸"
        primary={false}
      />
      <CensusCounts meta={meta} rollup={census.rollup} derived={census.derived} />
      <EditModePrompt {...prompt} />
      <ConfirmDialog
        open={confirmClear}
        title="Clear the roster?"
        message={`Everyone on the roster (${summary.employees} employees, ${summary.dependents} dependents) is removed. A later census import brings people back by who they are.`}
        confirmLabel="Clear roster"
        tone="danger"
        busy={Boolean(actions.busy.clear)}
        onConfirm={async () => {
          await actions.clear();
          setConfirmClear(false);
        }}
        onCancel={() => setConfirmClear(false)}
      />
    </>
  );
}
