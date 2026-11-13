import { useState } from 'react';
import { useSearchParams } from 'react-router';
import RequestPage from '../requestpage/RequestPage';
import LinkReady from './LinkReady';
import NewLink from './NewLink';

/*
 * The Request view (L24–L42; old 891f1b3 `DealReviewTab.jsx` request view): the request page — the who bar, the Ask
 * card on a person's link, their form, the settings card, edit mode, the tray going out — or "A new link…" (`?target=new`,
 * and the builder's doors `?preset=required | census-missing`, L41: landing writes nothing): the New link settings card
 * with what to ask, its live numbers and their form beside, then what Create link made. Done goes back to the page.
 */
export default function RequestView({ deal, meta, actions, asksClosed, next, onGo }) {
  const [params, setParams] = useSearchParams();
  const [result, setResult] = useState(null);
  const building = params.get('target') === 'new' || Boolean(params.get('preset'));
  const leave = () => {
    const nextParams = new URLSearchParams(params);
    ['target', 'preset'].forEach((key) => nextParams.delete(key));
    setParams(nextParams, { replace: true });
  };
  const open = () => {
    const nextParams = new URLSearchParams(params);
    nextParams.set('target', 'new');
    ['settings', 'edit'].forEach((key) => nextParams.delete(key));
    setParams(nextParams, { replace: true });
  };
  if (result) {
    return (
      <LinkReady
        result={result}
        actions={actions}
        onDone={() => {
          setResult(null);
          leave();
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
        <NewLink deal={deal} meta={meta} preset={params.get('preset') || ''} onCreated={setResult} onCancel={leave} />
      </>
    );
  }
  return <RequestPage deal={deal} meta={meta} actions={actions} asksClosed={asksClosed} next={next} onGo={onGo} onNewLink={open} />;
}
