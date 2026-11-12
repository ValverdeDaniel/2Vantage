// What other folders mount from the Intake tab (CLAUDE.md Map): the tab, the form's rows and badges that the
// Documents station's intake view lays out beside an intake file (E44; slice 65), the Coverage & marketing intent
// card, which the proposal builder mounts (J46; slice 26) and the RFP tab and the Overview will (B28, K12), and the
// Marketing readiness checklist, which the RFP tab and the Overview will mount (B28; slice 40).
export { default } from './IntakeTab';
export { default as ChecklistCard } from './ChecklistCard';
export { default as CoverageIntentCard } from './CoverageIntentCard';
export { badgeFor } from './badges';
export { buildSections } from './formModel';
