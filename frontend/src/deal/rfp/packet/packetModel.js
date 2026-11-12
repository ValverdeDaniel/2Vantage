// The packet card's ticks, pure (plan.md §8.12, §9.10; K34–K56; old CarriersTab.jsx TriTick, includeBody, RowNotes
// at 891f1b3). The server keeps only ticks that differ from the default (K35); these build what a click sends.

const plural = (count, noun) => `${count} ${noun}${count === 1 ? '' : 's'}`;

/** A row that can ride the packet: one that can be built (no census yet: K41), never a download-only row (K42). */
export const tickable = (row) => Boolean(row) && row.available !== false && row.packet_eligible !== false;

/** One section's rows, in the server's order (the old page's sections). */
export function sectionRows(packet, section) {
  return (packet?.rows || []).filter((row) => row.section === section);
}

/** "XLSX", "PDF", "CSV" for the Format column. */
export const formatWords = (row) => (row.file_format || 'file').toUpperCase();

/** The footer's line (K55): what "Download packet" zips, by name. */
export function membersWords(packet) {
  if (!packet?.count) return 'Nothing ticked yet — choose the documents this RFP should carry.';
  return `${plural(packet.count, 'document')}: ${(packet.members || []).join(' · ')}`;
}

/** A row's pill (K52): "Ready", "N problems", "Not signed"; null while the checks load. */
export function pillWords(pill) {
  if (!pill) return null;
  if (pill.status === 'ready') return { text: 'Ready', ok: true };
  if (pill.status === 'unsigned') return { text: 'Not signed', ok: false };
  return { text: plural(pill.count, 'problem'), ok: false };
}

/**
 * The ONE rule every bulk tick follows (D-063): write only disagreements. A row already where the target puts it is not
 * sent; a row moving TO its default is sent as null, so it follows the carrier picks again. "Select all" never ticks
 * what is off on purpose; "Deselect all" empties the packet outright.
 */
export function includeBody(rows, value) {
  const out = {};
  for (const row of (rows || []).filter(tickable)) {
    const target = value ? (row.deliberate ? Boolean(row.include) : true) : false;
    if (Boolean(row.include) === target) continue;
    out[row.key] = target === Boolean(row.default_include) ? null : target;
  }
  return out;
}

/** One row's click: its own tick, or null when it lands back on the default. */
export function tickBody(row, value) {
  return { [row.key]: value === Boolean(row.default_include) ? null : value };
}

/** The three-state box over some rows: ticked when every carrier-facing row is in, dashed when some are. */
export function triState(rows) {
  const eligible = (rows || []).filter(tickable);
  const facing = eligible.filter((row) => !row.deliberate);
  const on = eligible.filter((row) => row.include).length;
  const all = facing.length > 0 && facing.every((row) => row.include);
  return {
    eligible,
    on,
    total: eligible.length,
    offOnPurpose: eligible.filter((row) => row.deliberate && !row.include).length,
    all,
    some: on > 0 && !all,
  };
}

/** The "N of M in packet · K off on purpose" count beside a box. */
export function countWords(state) {
  const off = state.offOnPurpose > 0 ? ` · ${state.offOnPurpose} off on purpose` : '';
  return `${state.on} of ${state.total} in packet${off}`;
}

/** A tick that differs from what the carrier picks recommend ("your pick", K37). */
export const isPick = (row) => tickable(row) && Boolean(row.include) !== Boolean(row.default_include);

/** The collapsed packet card's line. */
export function packetSummary(packet) {
  return packet?.count > 0 ? `${plural(packet.count, 'document')} in the packet` : 'Nothing ticked yet';
}

/** The page as a tick leaves it, before the server answers (optimistic, K.6). */
export function optimisticTicks(packet, change) {
  if (!packet || !change) return packet;
  const rows = packet.rows.map((row) => {
    if (change === 'reset') return { ...row, include: tickable(row) && Boolean(row.default_include) };
    if (!(row.key in change)) return row;
    const value = change[row.key];
    return { ...row, include: tickable(row) && (value === null ? Boolean(row.default_include) : value) };
  });
  return { ...packet, rows, count: rows.filter((row) => row.include).length };
}

/** The format's sub-line in the grid: "Warner Pacific census · 23 columns · one row per member". */
export function rowSub(row) {
  return `${row.label} · ${row.columns} columns · one row per member`;
}
