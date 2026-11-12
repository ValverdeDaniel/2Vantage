// What other folders mount from Work with Claude (plan.md §8.17; CLAUDE.md: an index exports only what others mount).
// Slice 18: Claude's reads of the files on screen, with the staged review card (D28), under the Documents station.
// Slice 20: Work with Claude around every deal tab (the strip, the pill and the drawer, mounted once by the deal
// shell), the door tabs open it through (a kind, or the files dropped on them), "＋ Add quotes" (F96) and the
// quote-first door's drawer (D43).
export { default as ReadReviews } from './ReadReviews';
export { default as WorkWithClaude } from './WorkWithClaude';
export { default as AddQuotesButton, AddSbcsButton } from './AddQuotesButton';
export { default as QuoteDrop } from './QuoteDrop';
export { claudeDoor, claudeRoom } from './door';
// Slice 24: the plan table's lock switch on the Advisor's toolbar (F113, D104).
export { default as TableLock } from './TableLock';
// Slice 22: "＋ Add SBCs" on the board (F95) and "Attach SBC…" in a plan's ⋯ menu (D38).
export { useAttachSbc } from './AttachSbc';
// ✦ Ask Claude to re-check on a review strip (F66, E77): the station's List and strip and the Advisor's strip.
export { default as useRecheck } from './useRecheck';
