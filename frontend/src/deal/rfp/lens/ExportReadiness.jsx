import cx from '../../../ui/cx';
import useRfpDownload from '../useRfpDownload';
import { readinessCards, rowsWords, statusWords } from './lensModel';

/*
 * Export readiness (plan.md §8.12; K79; OQ63 keeps both these cards and the lens chips; old ExportReadiness.jsx at
 * 891f1b3, same classes): a card per carrier format this request sends — ready, or N things to fix — each opening its
 * lens on a click or Enter (Enter again closes it), and exporting every format it has. Export is always allowed: the
 * card says what is wrong rather than refusing; the check opens before the download (K69, slice 46).
 */
export default function ExportReadiness({ dealId, formats, active, onPick }) {
  const files = useRfpDownload(dealId);
  const { cards, sent } = readinessCards(formats);
  if (!cards.length) return null;
  return (
    <div className="bnf-xready" data-guide="census-export-readiness">
      <div className="bnf-xready-head">
        <b>Export readiness</b>
        <span className="bnf-review-note">
          {sent ? 'The carrier files this request sends.' : 'Every carrier format for this group.'}
        </span>
      </div>
      <div className="bnf-xready-cards">
        {cards.map((format) => {
          const words = statusWords(format);
          const pick = () => onPick(active === format.key ? '' : format.key);
          return (
            <div
              key={format.key}
              className={cx('bnf-xready-card', active === format.key && 'bnf-xready-card-on')}
              onClick={pick}
              role="button"
              tabIndex={0}
              aria-pressed={active === format.key}
              onKeyDown={(event) => event.key === 'Enter' && pick()}
            >
              <div className="bnf-xready-name">
                <b>{format.label}</b>
                <span>{rowsWords(format)}</span>
              </div>
              <div className="bnf-xready-foot">
                <span className={cx('bnf-xready-status', words.tone && `bnf-xready-${words.tone}`)}>{words.text}</span>
                {format.file_formats.map((kind, index) => {
                  const key = index === 0 ? format.key : `${format.key}-${kind}`;
                  return (
                    <button
                      key={kind}
                      type="button"
                      className="btn btn-secondary btn-sm"
                      disabled={files.busy === key}
                      onClick={(event) => {
                        event.stopPropagation();
                        files.download(key, `${format.carrier} census (${kind.toUpperCase()})`);
                      }}
                    >
                      {files.busy === key
                        ? 'Building…'
                        : `⬇ ${format.file_formats.length > 1 ? kind.toUpperCase() : 'Export'}`}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      {files.modal}
    </div>
  );
}
