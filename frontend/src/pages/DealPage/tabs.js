import { lazy } from 'react';

// The deal tabs built so far, each its own bundle (plan.md §3.9), mounted through its folder's index.js. A tab joins
// the sidebar (nav.js) when its slice adds it here.
export const TAB_COMPONENTS = {
  intake: lazy(() => import('../../deal/intake')),
  census: lazy(() => import('../../deal/census')),
  advisor: lazy(() => import('../../deal/advisor')),
  proposal: lazy(() => import('../../deal/proposal')),
  documents: lazy(() => import('../../deal/documents')),
};

export const BUILT_TABS = Object.keys(TAB_COMPONENTS);
