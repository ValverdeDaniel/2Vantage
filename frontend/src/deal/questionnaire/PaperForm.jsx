import { shownFields, shownValue } from './formModel';
import FieldRow from './FieldRow';
import Legend from './Legend';
import RowBlock from './RowBlock';

/*
 * The form laid out as the carrier's paper (G36): navy section bands, a three-column grid by width, red stars, italic
 * hints, the legend, and the row cards. What is on screen is the server's (`order`, `blocks`): a section's own
 * questions, its blocks, then the questions the carrier prints after them (`placement: after_blocks`, G21). An intro
 * that introduces a block goes with it (Florida Blue's "15. …" above the plans).
 *
 * The client's page shares it (slice 58, G83–G88) with three optional hooks: `lockedOf(slot)` (a broker's field the
 * client reads, G86), `canRemove(row)` (only a row their link added, G87) and `footOf(slot)` (a refusal, a conflict, a
 * colleague's answer under the question, as the old portal's `footOf`).
 */
export default function PaperForm({ spec, data, draft, onChange, onAddRow, onRemoveRow, disabled, ...hooks }) {
  const onScreen = new Set(data.order);
  const shownBlocks = new Set(data.blocks);
  const row = (field) => (
    <FieldRow
      key={field.key}
      spec={spec}
      field={field}
      slot={field.key}
      data={data}
      value={shownValue(data, draft, field.key)}
      onChange={onChange}
      disabled={disabled || Boolean(hooks.lockedOf?.(field.key))}
      foot={hooks.footOf?.(field.key)}
    />
  );
  return (
    <div className="bnf-q-form">
      {spec.sections.map((section) => {
        const fields = shownFields(section.fields, onScreen);
        const before = fields.filter((field) => field.placement !== 'after_blocks');
        const after = fields.filter((field) => field.placement === 'after_blocks');
        const blocks = section.blocks.filter((key) => shownBlocks.has(key));
        const introShown = section.blocks.length === 0 || blocks.length > 0;
        return (
          <section className="bnf-q-section" key={section.key} id={`bnf-q-sec-${section.key}`}>
            <h3 className="bnf-q-secthead">
              {section.number ? `Section ${section.number}. ` : ''}
              {section.label}
            </h3>
            {section.intro && <p className="bnf-q-intro">{section.intro}</p>}
            <div className="bnf-q-grid">{before.map(row)}</div>
            {section.intro_after_fields && introShown && <p className="bnf-q-intro">{section.intro_after_fields}</p>}
            {section.legend_intro && <p className="bnf-q-intro">{section.legend_intro}</p>}
            <Legend rows={section.legend} />
            {blocks.map((blockKey) => (
              <RowBlock
                key={blockKey}
                spec={spec}
                blockKey={blockKey}
                data={data}
                draft={draft}
                onChange={onChange}
                onAddRow={onAddRow}
                onRemoveRow={onRemoveRow}
                disabled={disabled}
                {...hooks}
              />
            ))}
            {after.length > 0 && <div className="bnf-q-grid">{after.map(row)}</div>}
          </section>
        );
      })}
    </div>
  );
}
