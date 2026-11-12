import { useRef, useState } from 'react';
import FileChips from './FileChips';
import FileRoom from './FileRoom';
import { kindLabel } from './drawerWords';
import ModelBar from './ModelBar';

/*
 * The drawer's panel (plan.md §8.17; D7, D8, D9, D13, D14, D16, D19; the old ScanChat's `bnf-scanchat`): the whole
 * panel takes dropped files ("Drop to attach…", D16; only file drags, the old fileDrag.js rules), the model picker and
 * the deal's spend, Chats ▾ (`chat.bar`, slice 24), the file chips on a tab whose files Claude reads (or the File room
 * where each file says what it is), the chat's messages (`chat.messages`), what Claude is doing and did (`children`),
 * then the composer (`chat.composer`) and 📎 Attach files. Before the deal exists (the quote-first door) only the drop
 * and 📎 show.
 */
const isFileDrag = (event) => Array.from(event.dataTransfer?.types || []).includes('Files');

export default function DrawerBody({ dealId, meta, state, kind, kinds, files, attach, model, onModel, chat = null, children }) {
  const picker = useRef(null);
  const depth = useRef(0);
  const [dropping, setDropping] = useState(false);
  const accept = kind ? meta.document_kinds.find((entry) => entry.key === kind)?.accept || [] : [];
  const label = kind ? kindLabel(meta, kind) : '';
  const lands = Boolean(state?.can?.opus);
  const reading = (state?.jobs || []).filter((job) => job.kind === 'read').flatMap((job) => job.documents);
  const drop = {
    onDragEnter: (event) => {
      if (!isFileDrag(event)) return;
      event.preventDefault();
      event.stopPropagation();
      depth.current += 1;
      setDropping(true);
    },
    onDragOver: (event) => {
      if (!isFileDrag(event)) return;
      event.preventDefault();
      event.stopPropagation();
      event.dataTransfer.dropEffect = 'copy';
    },
    onDragLeave: (event) => {
      if (!isFileDrag(event)) return;
      event.stopPropagation();
      depth.current = Math.max(0, depth.current - 1);
      if (!depth.current) setDropping(false);
    },
    onDrop: (event) => {
      if (!isFileDrag(event)) return;
      event.preventDefault();
      event.stopPropagation();
      depth.current = 0;
      setDropping(false);
      attach.attach(event.dataTransfer.files);
    },
  };

  return (
    <div className={`bb-panel bnf-scanchat${dropping ? ' is-dropping' : ''}`} data-claude-panel {...drop}>
      {dropping && (
        <div className="bnf-drop-overlay" aria-hidden="true">
          Drop to attach {label ? `them as ${label}` : 'the files'}
        </div>
      )}
      <div className="bb-panel-title">Work with Claude</div>
      <div className="bb-panel-sub">
        {kind
          ? `Attach the files, or drop them onto this panel: each is filed as ${label} and Claude reads it into the plans. `
          : 'Attach files, or drop them onto this panel, and say what each one is: Claude reads the kinds it reads and files the rest. '}
        {dealId &&
          (lands
            ? 'Your reads land at once, with ↶ Undo this run.'
            : 'Your reads wait here for your review before anything on the deal changes.')}
      </div>
      {state && <ModelBar dealId={dealId} meta={meta} state={state} model={model} onModel={onModel} disabled={attach.busy} />}
      {chat?.bar}
      {dealId && state && kind && (
        <FileChips
          dealId={dealId}
          files={files}
          kinds={kinds}
          meta={meta}
          readIds={state.read_documents || []}
          reading={reading}
          busy={attach.busy}
          onRead={attach.read}
        />
      )}
      {dealId && state && !kind && (
        <FileRoom
          dealId={dealId}
          files={files}
          meta={meta}
          readIds={state.read_documents || []}
          reading={reading}
          attach={attach}
        />
      )}
      {chat?.messages}
      {children}

      <div className="bnf-scanchat-input">
        <input
          ref={picker}
          type="file"
          multiple
          hidden
          accept={accept.join(',')}
          aria-label="Attach files"
          onChange={(event) => {
            attach.attach(event.target.files);
            event.target.value = '';
          }}
        />
        <button
          type="button"
          className="btn btn-secondary btn-sm bnf-scanchat-attach"
          disabled={attach.busy}
          title="Pick files — or drag them from your desktop onto this panel"
          onClick={() => picker.current?.click()}
        >
          {attach.busy ? 'Attaching…' : '📎 Attach files'}
        </button>
        {chat?.composer}
      </div>
    </div>
  );
}
