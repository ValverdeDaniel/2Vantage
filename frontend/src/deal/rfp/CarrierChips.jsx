import Chip from './Chip';
import { chipTitle, toggleBody } from './requestModel';

/*
 * The carrier chips, Medical then Ancillary (plan.md §8.12; K23–K25; old CarriersTab.jsx RequestPanel at 891f1b3, same
 * markup and classes): a picked chip is on; a carrier whose form or lines do not fit is dimmed and dashed, says why in
 * its tooltip, and stays clickable (advice, never a block); "own census" marks a carrier with its own census file. A
 * click sends only that carrier, added or removed (K25).
 */
export default function CarrierChips({ groups, chips, picked, onSave }) {
  return (groups || []).map((group) => (
    <div className="bnf-rfp-group" key={group.key} data-guide={`carriers-${group.key}`}>
      <div className="bnf-rfp-group-label">{group.label}</div>
      <div className="bnf-rfp-chips" role="group" aria-label={group.label}>
        {chips
          .filter((chip) => chip.group === group.key)
          .map((chip) => (
            <Chip
              key={chip.key}
              on={chip.selected}
              off={!chip.eligible}
              title={chipTitle(chip)}
              onClick={() => onSave(toggleBody('carriers', chip.key, picked))}
            >
              {chip.name}
              {chip.census_format && <span className="bnf-rfp-chip-tag">own census</span>}
            </Chip>
          ))}
      </div>
    </div>
  ));
}
