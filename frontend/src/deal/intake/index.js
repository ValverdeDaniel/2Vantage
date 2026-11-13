// What other folders mount from the Intake tab (CLAUDE.md Map): the tab, the form's rows and badges that the
// Documents station's intake view lays out beside an intake file (E44; slice 65), the Coverage & marketing intent
// card, which the proposal builder mounts (J46; slice 26) and the RFP tab and the Overview will (B28, K12), and the
// Marketing readiness checklist, which the RFP tab and the Overview will mount (B28; slice 40), and Mark as marketed,
// which the RFP's Emails card offers once a draft is sent (K33; slice 46). The Overview's Card 1 draws the same
// checklist rows in its own frame and needs the same controls (M.6; B30 "one set of controls, two frames"; slice 63):
// the rows' writes, their status and controls, and the form picker.
export { default } from './IntakeTab';
export { default as ChecklistCard } from './ChecklistCard';
export { default as CoverageIntentCard } from './CoverageIntentCard';
export { default as MarketButton } from './MarketButton';
export { badgeFor } from './badges';
export { buildSections } from './formModel';
export { default as FormPicker } from './FormPicker';
export { default as useChecklistWrites } from './useChecklistWrites';
export { controlsOf, statusOf } from './checklistModel';
