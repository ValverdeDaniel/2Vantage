// The Review & requests tab, as the deal shell mounts it (CLAUDE.md: a tab folder's index.js exports only what others
// mount), the section bar Intake and Census mount at their top (L14, C34; slice 55), and the request tray's dock the
// deal shell mounts under every tab (L49, L50; slice 56). The overlay joins here with slice 57.
export { default } from './ReviewTab';
export { default as SectionBar } from './section/SectionBar';
export { default as TrayDock } from './tray/TrayDock';
