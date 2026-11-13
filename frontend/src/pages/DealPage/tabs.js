import { lazy } from 'react';

// The deal tabs built so far, each its own bundle (plan.md §3.9), mounted through its folder's index.js. A tab joins
// the sidebar (nav.js) when its slice adds it here.
export const TAB_COMPONENTS = {
  overview: lazy(() => import('../../deal/overview')), // the tab a deal opens on (Part M; slice 62)
  agenda: lazy(() => import('../../deal/agenda')), // steps, marks and tasks (Part I; slice 60)
  review: lazy(() => import('../../deal/review')), // Review & requests (Part L; slice 53's V1, the portal from 54)
  intake: lazy(() => import('../../deal/intake')),
  census: lazy(() => import('../../deal/census')),
  questionnaire: lazy(() => import('../../deal/questionnaire')), // shown in the sidebar only while the deal has a form (G7)
  rfp: lazy(() => import('../../deal/rfp')), // the RFP tab (K1; slices 44–46)
  commission: lazy(() => import('../../deal/commission')), // rates, expected revenue and the split (H1–H24; slice 48)
  advisor: lazy(() => import('../../deal/advisor')),
  proposal: lazy(() => import('./ProposalRoute')), // the packet card over the Advisor's board, composed here (J.3.6)
  documents: lazy(() => import('../../deal/documents')),
};

export const BUILT_TABS = Object.keys(TAB_COMPONENTS);
