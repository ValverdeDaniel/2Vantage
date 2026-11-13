// The Overview tab (plan.md §8.6; Part M; slices 62–63). Only what others mount is exported (slice 4's rule): the tab,
// and the parts the client page mounts (plan.md §8.5; slice 67): the Timeline (a feed of the Activity shape, by deal
// or by path), the notes card (a deal's notepad), the commission and coverage-notes side cards, the Waiting banner
// (the deal in flight's, over its `journey/` read), and the outreach strip with "Who we've asked" above the Timeline.
export { default } from './OverviewTab';
export { default as Timeline } from './feed/Timeline';
export { default as NotesCard } from './notes/NotesCard';
export { default as CommissionCard } from './CommissionCard';
export { default as CoverageNotesCard } from './CoverageNotesCard';
export { default as WaitingBanner } from './WaitingBanner';
export { default as OutreachStrip } from './feed/OutreachStrip';
export { default as AskedList } from './feed/AskedList';
