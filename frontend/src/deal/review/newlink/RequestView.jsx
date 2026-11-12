import { useState } from 'react';
import LinkReady from './LinkReady';
import NewLink from './NewLink';

/*
 * The Request view, as slice 53 builds it (L40; old 891f1b3 `DealReviewTab.jsx` request view): its title, and a new
 * link — the settings card, then what Create link made. The who bar, the ask rail, their form, the tray's cart and
 * edit mode arrive with slices 56–57. Done goes to the Board, where the new request waits.
 */
export default function RequestView({ deal, meta, actions, onDone, asksClosed }) {
  const [result, setResult] = useState(null);
  return (
    <>
      <div className="rr-reqpage-title rr-reqpage-top">
        <div className="bb-tab-title">Request</div>
        <div className="bb-subtitle">Ask for what is missing, check what comes back, and keep every link up to date.</div>
      </div>
      {asksClosed && <div className="bb-banner">{asksClosed}</div>}
      {!asksClosed && !result && <NewLink deal={deal} meta={meta} onCreated={setResult} onCancel={onDone} />}
      {result && (
        <LinkReady
          result={result}
          actions={actions}
          onDone={() => {
            setResult(null);
            onDone();
          }}
        />
      )}
    </>
  );
}
