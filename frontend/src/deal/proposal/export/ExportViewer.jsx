import DeckViewer from './DeckViewer';
import { chooseFile } from './exportFiles';
import FileChips from './FileChips';
import WorkbookViewer from './WorkbookViewer';

/*
 * The Export viewer, the Advisor's last view (plan.md §8.14; F3, F136, J105, J107–J115; the old ExportViewer.jsx at
 * 891f1b3): the client files as they would download now, before anyone downloads them. This is the shell: the file
 * chips and the view that draws the file picked. `file` is the Advisor's (`?file=`, else the one picked last in this
 * browser); `place` holds where each view stands ({excel: tab title, deck: {title, nth, index} or {line}}), kept by the
 * Advisor so a switch to the builder and back finds it, and each view's copy stays in React Query's cache meanwhile.
 *
 * The spreadsheet is the Excel view (slice 28). PowerPoint, PDF and Paper are one DeckViewer over one build (slice 30),
 * so switching between them never builds again and keeps the slide; "Not printing" opens the builder (`onGoBuild`).
 */
export default function ExportViewer({ dealId, file: wanted, onFile, place, onPlace, onGoBuild }) {
  const file = chooseFile(wanted);
  const chips = <FileChips file={file} onFile={onFile} />;
  if (file !== 'excel') {
    return (
      <DeckViewer
        dealId={dealId}
        file={file}
        chips={chips}
        selected={place?.deck ?? null}
        onSelect={(deck) => onPlace({ ...place, deck })}
        onGoBuild={onGoBuild}
      />
    );
  }
  return (
    <WorkbookViewer
      dealId={dealId}
      chips={chips}
      selected={place?.excel ?? null}
      onSelect={(title) => onPlace({ ...place, excel: title })}
    />
  );
}
