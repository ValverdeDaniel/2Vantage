/*
 * A line the coverage intent keeps off the client's documents says so at the top of its Plans card, with the way back
 * on (plan.md §8.14; J30; the old `bnf-build-offline` at 891f1b3). "Left off" opens the intent card (on the Intake
 * tab until the builder mounts it, J46); a line the intent never names can be put on from here, through intake's one
 * writer: as a line they have today, or as new coverage.
 */
export default function OffNotice({ line, busy, onOpenIntent, onPutOn }) {
  if (!line.off) return null;
  const leftOff = line.off.reason === 'left_off';
  return (
    <div className="bnf-build-offline" role="status">
      <span>
        <b>Off the proposal.</b>{' '}
        {leftOff
          ? 'The Coverage & marketing intent says Leave off, so no client document carries this line, whatever is ' +
            'starred here.'
          : 'This line has quotes but is not in the Coverage & marketing intent, so no client document carries it.'}
      </span>
      <span className="bnf-build-offline-actions">
        {leftOff ? (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onOpenIntent}>
            Open the intent card ▸
          </button>
        ) : line.currents.length ? (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={busy}
            title="Add this line to the intent as a line we quote"
            onClick={() => onPutOn(true)}
          >
            Put it on
          </button>
        ) : (
          <>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={busy}
              title="Add it to the intent as coverage the client has today, shopped this year"
              onClick={() => onPutOn(true)}
            >
              Put it on — they have it today
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={busy}
              title="Add it to the intent as new coverage, quoted this year"
              onClick={() => onPutOn(false)}
            >
              Put it on — as new coverage
            </button>
          </>
        )}
      </span>
    </div>
  );
}
