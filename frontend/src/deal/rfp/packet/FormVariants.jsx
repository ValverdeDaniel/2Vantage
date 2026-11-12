import Chip from '../Chip';

/*
 * Warner's request form in three shapes (plan.md §9.9; K46; old CarriersTab.jsx at 891f1b3): Simplified is Warner's
 * standard at every size; the 2–50 and 51+ forms are dimmed where the band does not fit them and stay pickable. A pick
 * writes `form` and takes the packet card's mark off (K10). Whether the deal goes through Warner at all is the route.
 */
export default function FormVariants({ row, onPick }) {
  return (
    <div className="bnf-rfp-chips bnf-rfp-variants" data-guide="rfp-form-variants">
      {row.options.map((option) => (
        <Chip
          key={option.key}
          on={option.key === row.variant}
          off={!option.applicable}
          title={option.applicable ? `Warner ${option.version}` : `Usually for ${option.size} groups`}
          onClick={() => option.key !== row.variant && onPick(option.key)}
        >
          {option.label}
          {option.recommended && <span className="bnf-rfp-chip-tag">standard</span>}
        </Chip>
      ))}
    </div>
  );
}
