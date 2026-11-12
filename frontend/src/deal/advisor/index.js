// The Advisor tab, as the deal shell mounts it (CLAUDE.md: a tab folder's index.js exports only what others mount).
export { default } from './AdvisorTab';
// The quote reader's body for the staged review card, which deal/claude/ mounts on Documents (D28; slice 18).
export { default as QuoteReview } from './claude/QuoteReview';
