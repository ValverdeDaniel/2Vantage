import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { markSeen, useRequestPage, useTray, useTrayAsk, useTrayRemove, useTraySend } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import cx from '../../../ui/cx';
import { useToast } from '../../../ui/useToast';
import LinkReady from '../newlink/LinkReady';
import useItemThread from '../thread/useItemThread';
import { sentWords } from '../tray/trayModel';
import AskRail from './AskRail';
import ChooseWho from './ChooseWho';
import GoingOut from './GoingOut';
import ItemCard from './ItemCard';
import { needYou, paneOf, SHOWS, showOf, shown } from './requestModel';
import WhoBar from './WhoBar';

const SEEN_AFTER_MS = 5000; // a look counts once the page was up this long (L44)
const pairs = (list) => Object.fromEntries((list || []).map(({ key, label }) => [key, label]));

/*
 * The request page (plan.md §8.8; L24, L26–L29, L33, L37, L53; B12; old 891f1b3 `RequestPage.jsx`): where a person
 * works with one client. The head says how many things need us; the who bar who has a link; the tabs (`?pane=`:
 * Intake, Census, Documents) each read alone; Show (`?show=`) narrows the ask list by where items stand. Left, the ask
 * list: a tick puts an item in the request tray. Middle, Going out: the tray by the link it goes on, and Send. Right,
 * the picked item's card with its thread. Leaving after 5 s marks this person's last look (L33). Their form beside the
 * list, the comment margin and edit mode are slice 57's.
 */
export default function RequestPage({ deal, meta, actions, asksClosed, onNewLink }) {
  const [params, setParams] = useSearchParams();
  const pane = paneOf(params);
  const show = showOf(params);
  const page = useRequestPage(deal.id, pane);
  const tray = useTray(deal.id);
  const ask = useTrayAsk(deal.id);
  const remove = useTrayRemove(deal.id);
  const sender = useTraySend(deal.id);
  const toast = useToast();
  const readOnly = Boolean(asksClosed);
  const thread = useItemThread(deal.id, { readOnly });
  const [picked, setPicked] = useState(null);
  const [choosing, setChoosing] = useState(null);
  const [result, setResult] = useState(null);
  const [made, setMade] = useState(null);

  useEffect(() => {
    const opened = Date.now();
    return () => {
      if (Date.now() - opened >= SEEN_AFTER_MS) markSeen(deal.id).catch(() => {});
    };
  }, [deal.id]);

  const setParam = (key, value, fallback) => {
    const next = new URLSearchParams(params);
    if (value === fallback) next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  };
  const run = (promise, words) => promise.then((answer) => words && toast.success(words(answer))).catch((error) => toast.error(errorText(error)));
  const railActions = {
    onAsk: (refs, extra = {}) => run(ask.mutateAsync({ refs, ...extra }), (answer) => `${answer.added} added to the request tray`),
    onAskColumn: (column) => run(ask.mutateAsync({ census: { columns: [column], scope: 'blank' } }), (answer) => `${answer.added} added to the request tray`),
    onRemove: (id) => run(remove.mutateAsync([id])),
    onPick: (ref) => setPicked(ref),
  };
  const send = (body) =>
    sender
      .mutateAsync(body)
      .then((answer) => {
        toast.success(sentWords(answer));
        if (answer.links) setMade(answer);
        else setResult(answer);
        setChoosing(null);
      })
      .catch((error) => toast.error(errorText(error)));

  if (page.isPending || tray.isPending) return <Loading label="Loading the request page…" />;
  if (page.isError) return <InlineError title="The request page" error={page.error} onRetry={() => page.refetch()} />;
  const data = page.data;
  const labels = pairs(meta?.rail_statuses);
  const items = shown(data.items, show);
  const item = data.items.find((entry) => entry.ref === picked) || null;
  const busy = ask.isPending || remove.isPending || sender.isPending;
  const need = needYou(data.panes);
  return (
    <div className="rr-reqpage-wrap">
      <div className="rr-reqpage-title rr-reqpage-top">
        <div className="bb-tab-title">Request</div>
        <div className="bb-subtitle">
          Ask for what is missing, check what comes back, and keep every link up to date.
          {need > 0 && ` ${need} need${need === 1 ? 's' : ''} you.`}
        </div>
      </div>
      {asksClosed && <div className="rr-reqpage-refusal">{asksClosed}</div>}
      <WhoBar people={data.people} actions={actions} readOnly={readOnly} onNewLink={onNewLink} />
      <div className="bnf-advisor-views bnf-board-views" role="group" aria-label="Tab">
        <span className="bnf-advisor-views-label">Tab</span>
        {data.panes.map((entry) => (
          <button key={entry.key} type="button" className={cx('bnf-viewtab', entry.key === pane && 'bnf-viewtab-on')} aria-pressed={entry.key === pane} onClick={() => setParam('pane', entry.key, 'intake')}>
            {entry.label}
            {entry.waiting + entry.in_cart > 0 ? ` · ${entry.waiting + entry.in_cart}` : ''}
          </button>
        ))}
        <span className="bnf-advisor-views-label">Show</span>
        {SHOWS.map((entry) => (
          <button key={entry.key} type="button" className={cx('bnf-viewtab', entry.key === show && 'bnf-viewtab-on')} aria-pressed={entry.key === show} onClick={() => setParam('show', entry.key, 'all')}>
            {entry.label} · {data.counts[entry.key] ?? 0}
          </button>
        ))}
      </div>
      {data.new.length > 0 && (
        <div className="rr-reqpage-new" role="status">
          <b>{data.new.length} new since your last look</b>
          <span> · {data.new.map((ref) => data.items.find((entry) => entry.ref === ref)?.label || ref).join(', ')}</span>
        </div>
      )}
      <div className="rr-reqpage">
        <div className="rr-reqpage-rail">
          <AskRail page={data} items={items} labels={labels} readOnly={readOnly} busy={busy} picked={picked} actions={railActions} />
        </div>
        <div className="rr-reqpage-cart">
          {made && <LinkReady result={made} actions={actions} onDone={() => setMade(null)} />}
          {choosing && <ChooseWho deal={deal} count={choosing.length} busy={sender.isPending} onSend={(who) => send({ ids: choosing, new: who })} onCancel={() => setChoosing(null)} />}
          <GoingOut tray={tray.data} sections={meta?.tray_sections} readOnly={readOnly} busy={busy} result={result} onSend={send} onRemove={railActions.onRemove} onChooseWho={setChoosing} onDismiss={() => setResult(null)} />
        </div>
        <div className="rr-reqpage-cards">
          <ItemCard item={item} thread={data.threads[picked] || []} labels={labels} kindWords={pairs(meta?.note_kinds)} newSince={data.seen_at} readOnly={readOnly} propsFor={thread.propsFor} onClose={() => setPicked(null)} />
        </div>
      </div>
    </div>
  );
}
