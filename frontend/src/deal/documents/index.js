// What other folders mount from the Documents tab (CLAUDE.md Map): the tab, and the file's own window, which App.jsx
// routes at /deals/:dealId/documents/:docId/window (E69–E71; slice 65). ↗ for a value's cell is viewer/SourcePin, shared
// code, so a tab that shows a pin never loads the station or pdf.js.
export { default } from './DocumentsTab';
export { default as DocumentWindowPage } from './DocumentWindowPage';
// The Advisor's "As quoted" (F42; slice 21): a scanned quote as printed, on the station's Grid. The Advisor loads it
// lazily, so the board never loads the station.
export { default as AsQuotedBoard } from './grid/AsQuotedBoard';
