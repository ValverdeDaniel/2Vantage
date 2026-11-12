import { shownFields, slotKey } from './formModel';

/*
 * The Table layout's rows (G37), in the Form's order: a section's questions, each repeating row's questions (the
 * first carrying the row's Remove), the block's "＋ Add …", then the questions printed after the blocks. Pure.
 */
export function tableRows(spec, data) {
  const onScreen = new Set(data.order);
  const shownBlocks = new Set(data.blocks);
  const out = [];
  const scalar = (section) => (field) => out.push({ key: field.key, group: section.label, field, block: '', rowId: 0 });
  spec.sections.forEach((section) => {
    const fields = shownFields(section.fields, onScreen);
    fields.filter((field) => field.placement !== 'after_blocks').forEach(scalar(section));
    section.blocks
      .filter((blockKey) => shownBlocks.has(blockKey))
      .forEach((blockKey) => {
        const block = spec.blocks[blockKey];
        const rows = data.rows?.[blockKey] || [];
        rows.forEach((row) => {
          shownFields(block.fields, onScreen, blockKey, row.id).forEach((field, at) =>
            out.push({
              key: slotKey(blockKey, row.id, field.key),
              group: `${block.row_label} ${row.number}`,
              field,
              block: blockKey,
              rowId: row.id,
              firstOfRow: at === 0,
            }),
          );
        });
        out.push({ key: `add:${blockKey}`, addBlock: blockKey, count: rows.length });
      });
    fields.filter((field) => field.placement === 'after_blocks').forEach(scalar(section));
  });
  return out;
}
