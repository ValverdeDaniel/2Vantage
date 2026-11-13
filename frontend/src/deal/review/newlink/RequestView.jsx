import { useState } from 'react';
import RequestPage from '../requestpage/RequestPage';
import LinkReady from './LinkReady';
import NewLink from './NewLink';

/*
 * The Request view (L24–L40; old 891f1b3 `DealReviewTab.jsx` request view): the request page (slice 56: who has a link,
 * what each tab could ask, the request tray going out, each item's thread), or "A new link…": the settings card, then
 * what Create link made. Done goes back to the page. The builder in full, the Ask card and edit mode are slice 57's.
 */
export default function RequestView({ deal, meta, actions, asksClosed }) {
  const [building, setBuilding] = useState(false);
  const [result, setResult] = useState(null);
  if (result) {
    return (
      <LinkReady
        result={result}
        actions={actions}
        onDone={() => {
          setResult(null);
          setBuilding(false);
        }}
      />
    );
  }
  if (building && !asksClosed) {
    return (
      <>
        <div className="rr-reqpage-title rr-reqpage-top">
          <div className="bb-tab-title">Request</div>
          <div className="bb-subtitle">A new link: who gets it, what it asks, and who can open it.</div>
        </div>
        <NewLink deal={deal} meta={meta} onCreated={setResult} onCancel={() => setBuilding(false)} />
      </>
    );
  }
  return <RequestPage deal={deal} meta={meta} actions={actions} asksClosed={asksClosed} onNewLink={() => setBuilding(true)} />;
}
