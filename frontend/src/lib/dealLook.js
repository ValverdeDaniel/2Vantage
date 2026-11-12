// How a deal draws in the old look: its stage pill (`bb-stage-pill` plus one class per stage; M15, I76), its client
// status badge and the avatar initials. Labels come from /api/meta/ (rule 1); these are only classes. The old ladder had
// no `proposal`: it takes the old "with the client" violet pill. An unknown stage draws as intake, as the old one did.
const PILLS = {
  intake: 'bb-stage-extracting',
  quoting: 'bb-stage-review',
  proposal: 'bb-stage-client',
  sold: 'bb-stage-complete',
  lost: 'bb-stage-lost',
};

/** 'bb-stage-pill bb-stage-…' for a stage key. */
export function stagePillClass(stage) {
  return `bb-stage-pill ${PILLS[stage] || PILLS.intake}`;
}

// The client status badge (§5.1): Prospect grey, New client green, Existing client violet.
const STATUS_BADGES = {
  prospect: 'bb-badge-gray',
  new_client: 'bb-badge-green',
  existing_client: 'bb-badge-violet',
};

/** 'bb-badge bb-badge-…' for a client status key. */
export function statusBadgeClass(status) {
  return `bb-badge ${STATUS_BADGES[status] || STATUS_BADGES.prospect}`;
}

/** Two initials for the old avatar square: "Golden Dental Group" → "GD". */
export function initialsOf(name) {
  return String(name || '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase();
}
