import cx from '../../../ui/cx';
import { badgeOf, chipSub } from './lensModel';

/*
 * The chip row above the census (plan.md §8.12; K80; old CensusFormatLens.jsx LensChips at 891f1b3): "Our census" (the
 * roster itself), then every carrier format with its counts and whether it is in the packet. Keys are the RFP
 * packet's own, so its "Check ▸" lands here. Warner's forms with the census inside join with slice 46 (K42).
 */
export default function LensChips({ formats, active, onPick }) {
  return (
    <div className="bb-acord-picker bnf-lens-chips" data-guide="census-lens-chips">
      <button
        type="button"
        className={cx('bb-acord-chip bnf-lens-chip', !active && 'active')}
        aria-pressed={!active}
        onClick={() => onPick('')}
      >
        <span className="bb-acord-chip-num">≡</span>
        <span className="bb-acord-chip-body">
          <span className="bb-acord-chip-title">Our census</span>
          <span className="bb-acord-chip-sub">every column, and who answers it</span>
        </span>
      </button>
      {formats.length > 0 && <span className="bnf-lens-sep">Carrier formats</span>}
      {formats.map((format) => (
        <button
          key={format.key}
          type="button"
          className={cx('bb-acord-chip bnf-lens-chip', active === format.key && 'active')}
          aria-pressed={active === format.key}
          data-guide-lens={format.key}
          title={format.label}
          onClick={() => onPick(format.key)}
        >
          <span className="bb-acord-chip-num">{badgeOf(format.carrier)}</span>
          <span className="bb-acord-chip-body">
            <span className="bb-acord-chip-title">
              {format.carrier}
              {format.file_formats.length > 1 && (
                <span className="bnf-lens-chip-fmts">
                  {' '}
                  {format.file_formats.map((x) => x.toUpperCase()).join(' | ')}
                </span>
              )}
            </span>
            <span className="bb-acord-chip-sub">{chipSub(format)}</span>
          </span>
        </button>
      ))}
    </div>
  );
}
