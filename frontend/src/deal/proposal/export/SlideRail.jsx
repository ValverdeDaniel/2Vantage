import cx from '../../../ui/cx';
import PageCanvas from './PageCanvas';

const THUMB_WIDTH = 176;

/*
 * The deck view's rail (plan.md §8.14; J109; the old ExportViewer rail at 891f1b3): a thumbnail of every slide with its
 * number and title, the one on screen ringed, and a plan set's fit dot when its table did not simply fit (J110).
 */
export default function SlideRail({ slides, index, doc, verdicts, noun, onGo }) {
  const Noun = noun[0].toUpperCase() + noun.slice(1);
  return (
    <div className="bnf-xv-rail" aria-label={`${Noun}s`}>
      {slides.map((s, i) => (
        <button
          key={`${s.n}-${s.title}`}
          type="button"
          className={cx('bnf-xv-thumb', i === index && 'bnf-xv-thumb-on')}
          onClick={() => onGo(i)}
          aria-current={i === index ? 'true' : undefined}
        >
          <PageCanvas doc={doc} number={s.n} width={THUMB_WIDTH} />
          <span className="bnf-xv-thumb-label">
            <span className="bnf-xv-thumb-n">{s.n}</span>
            {verdicts[i] && verdicts[i].level !== 'ok' && (
              <span
                className={`bnf-xv-dot bnf-xv-dot-${verdicts[i].level}`}
                title={verdicts[i].words}
                aria-hidden="true"
              />
            )}
            {s.title || (s.kind === 'cover' ? 'Cover' : '')}
          </span>
        </button>
      ))}
    </div>
  );
}
