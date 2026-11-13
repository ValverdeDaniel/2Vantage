// The Agenda tab, as the deal shell mounts it (CLAUDE.md: a tab folder's index.js exports only what others mount), and
// the pieces the client page's Agenda mounts for each of its deals (slice 68; CL24): the sections, a row, the task
// form and the actions they share.
export { default } from './AgendaTab';
export { default as AgendaSections } from './AgendaSections';
export { default as AgendaRow } from './AgendaRow';
export { default as TaskForm } from './TaskForm';
export { default as useAgendaActions } from './useAgendaActions';
