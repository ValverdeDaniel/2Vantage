// The readers' bodies for the review card (plan.md §10.5; D28): the quote reader's lives with the Advisor and loads
// only when a card shows one, so the deal shell, which mounts Work with Claude on every tab, never loads the Advisor.
import { lazy } from 'react';

const quoteReview = lazy(() => import('../advisor').then((module) => ({ default: module.QuoteReview })));

// An SBC read's change set has the quote reader's shape (slice 22), so the same body shows it.
export const RENDERERS = { quotes: quoteReview, sbc: quoteReview };
