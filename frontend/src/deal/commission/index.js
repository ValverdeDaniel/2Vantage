// The Commission tab, as the deal shell mounts it (CLAUDE.md: a tab folder's index.js exports only what others
// mount), and the split editor, which the client page mounts in client scope (H106; slice 68).
export { default } from './CommissionTab';
export { default as SplitEditor } from './SplitEditor';
// The booking summary after a sale, which the deal page opens over any tab (H35; slice 49).
export { default as BookingSummaryModal } from './BookingSummaryModal';
