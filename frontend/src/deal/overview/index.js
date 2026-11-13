// The Overview tab (plan.md §8.6; Part M; slices 62–63). Only what others mount is exported (slice 4's rule): the tab,
// and the parts the client page mounts (plan.md §8.5; slice 67): the Timeline (a feed of the Activity shape, by deal
// or by path), the notes card (a deal's notepad), and the commission and coverage-notes side cards.
export { default } from './OverviewTab';
export { default as Timeline } from './feed/Timeline';
export { default as NotesCard } from './notes/NotesCard';
export { default as CommissionCard } from './CommissionCard';
export { default as CoverageNotesCard } from './CoverageNotesCard';
