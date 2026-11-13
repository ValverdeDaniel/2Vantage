import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router';
import { useRequests } from '../../../api/reviewForm';
import { markSeen, useRequestPage, useTray, useTrayAsk, useTrayRemove, useTraySend } from '../../../api/reviewTray';
import { errorText } from '../../../lib/errors';
import InlineError from '../../../ui/InlineError';
import Loading from '../../../ui/Loading';
import cx from '../../../ui/cx';
import { useToast } from '../../../ui/useToast';
import NextBanner from '../board/NextBanner';
import EditMode from '../edit/EditMode';
import LinkReady from '../newlink/LinkReady';
import LinkSettingsCard from '../settings/LinkSettingsCard';
import PeopleLinks from '../settings/PeopleLinks';
import { linkStatus, peopleOf } from '../settings/settingsModel';
import useItemThread from '../thread/useItemThread';
import { sentWords } from '../tray/trayModel';
import AskRail from './AskRail';
import { bodyOf, targetOf } from './askCardModel';
import askMode from './askMode';
import ChooseWho from './ChooseWho';
import GoingOut from './GoingOut';
import ItemCard from './ItemCard';
import MarginColumn from './MarginColumn';
import OurRows from './OurRows';
import { needYou, paneOf, SHOWS, showOf, shown } from './requestModel';
import TheirForm from './TheirForm';
import useAskCard from './useAskCard';
import WhoBar from './WhoBar';

const QUEUE_OF = { census: 'census', questionnaire: 'questionnaire' }; // a tab's Review ▸: its section's queue

const SEEN_AFTER_MS = 5000; // a look counts once the page was up this long (L44)
const pairs = (list) => Object.fromEntries((list || []).map(({ key, label }) => [key, label]));

/*
 * The request page (plan.md §8.8; L24–L42; B12; old 891f1b3 `RequestPage.jsx`): where a person works with one client.
 * The head says what needs us and what to do next (L25); the who bar who has a link (L26) — All people, where a tick
 * waits in the request tray, or one person, where the Ask card shows what THEIR link asks and their form fills the
 * middle (L30, L42; `?target=link:<id>`) — and their settings card (`?settings=<id>`, L39) and People & links (L38).
 * The tabs (`?pane=`) each read alone; Show narrows the list. Middle: Going out (the tray, L37) over our form (L30), their form, or edit mode
 * (`?edit=1`, L34–L35: double-click a row). Right: the picked item's card, or on a person's link the comment margin
 * beside their form (L31). Leaving after 5 s marks this person's last look (L33).
 */
export default function RequestPage({ deal, meta, actions, asksClosed, next, onGo, onNewLink }) {
  const [params, setParams] = useSearchParams();
  const pane = paneOf(params);
  const show = showOf(params);
  const target = targetOf(params);
  const settingsId = Number(params.get('settings')) || null;
  const editing = params.get('edit') === '1';
  const requests = useRequests(deal.id);
  const people = peopleOf(requests.data?.requests);
  const pickedPerson = target?.kind === 'link' ? people.find((person) => person.link_id === target.id) : null;
  const page = useRequestPage(deal.id, pane, pickedPerson?.request_id || null);
  const askTarget = pickedPerson && page.data?.target?.request_id === pickedPerson.request_id ? page.data.target : null;
  const card = useAskCard(deal.id, askTarget);
  const tray = useTray(deal.id);
  const ask = useTrayAsk(deal.id);
  const remove = useTrayRemove(deal.id);
  const sender = useTraySend(deal.id);
  const toast = useToast();
  const readOnly = Boolean(asksClosed);
  const thread = useItemThread(deal.id, { readOnly });
  const frameRef = useRef(null);
  const [picked, setPicked] = useState(null);
  const [choosing, setChoosing] = useState(null);
  const [result, setResult] = useState(null);
  const [made, setMade] = useState(null);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    const opened = Date.now();
    return () => {
      if (Date.now() - opened >= SEEN_AFTER_MS) markSeen(deal.id).catch(() => {});
    };
  }, [deal.id]);

  const write = (change) => {
    const nextParams = new URLSearchParams(params);
    Object.entries(change).forEach(([key, value]) => (value ? nextParams.set(key, value) : nextParams.delete(key)));
    setParams(nextParams, { replace: true });
  };
  const run = (promise, words) => promise.then((answer) => words && toast.success(words(answer))).catch((error) => toast.error(errorText(error)));
  const railActions = {
    onAsk: (refs, extra = {}) => run(ask.mutateAsync({ refs, ...extra }), (answer) => `${answer.added} added to the request tray`),
    onAskColumn: (column) => run(ask.mutateAsync({ census: { columns: [column], scope: 'blank' } }), (answer) => `${answer.added} added to the request tray`),
    onRemove: (id) => run(remove.mutateAsync([id])),
    onPick: (ref) => setPicked(ref),
    onEdit: () => !readOnly && write({ edit: '1' }),
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
  const pickPerson = (person) => write({ target: person ? `link:${person.link_id}` : '', settings: '' });
  const editPerson = (person) => {
    setDrawer(false);
    const live = linkStatus(person) === 'active';
    write({ settings: String(person.link_id), target: live ? `link:${person.link_id}` : params.get('target') || '' });
  };

  if (page.isPending || tray.isPending) return <Loading label="Loading the request page…" />;
  if (page.isError) return <InlineError title="The request page" error={page.error} onRetry={() => page.refetch()} />;
  const data = page.data;
  const labels = pairs(meta?.rail_statuses);
  const items = shown(data.items, show);
  const item = data.items.find((entry) => entry.ref === picked) || null;
  const busy = ask.isPending || remove.isPending || sender.isPending || card.busy;
  const need = needYou(data.panes);
  const settingsPerson = people.find((person) => person.link_id === settingsId) || null;
  const mode = askTarget ? askMode({ card, target: askTarget, meta, pane, labels, readOnly }) : null;
  const who = pickedPerson?.name || (pickedPerson ? 'the private link' : '');
  const previewBody = askTarget ? { request_id: askTarget.request_id, link_id: pickedPerson.link_id, ...bodyOf(card.change, askTarget) } : null;
  const cardProps = { item, thread: data.threads[picked] || [], labels, kindWords: pairs(meta?.note_kinds), newSince: data.seen_at, readOnly, propsFor: thread.propsFor };
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
      <NextBanner entries={next} kinds={meta?.next_kinds} onGo={onGo} onExtend={actions.extend} readOnly={readOnly} />
      <WhoBar people={data.people} picked={pickedPerson?.link_id || null} waiting={askTarget && card.count ? { [askTarget.request_id]: true } : null}
        actions={actions} readOnly={readOnly} total={people.length} onPick={pickPerson} onEdit={editPerson} onNewLink={onNewLink} onPeople={() => setDrawer(true)} />
      {target?.kind === 'link' && pickedPerson && !askTarget && !page.isFetching && (
        <div className="rr-edit-note" role="status">{pickedPerson.name || 'This link'} can no longer take a change: edit its settings, or make a new link.</div>
      )}
      {settingsPerson && (
        <LinkSettingsCard key={settingsPerson.link_id} deal={deal} person={settingsPerson} meta={meta} actions={actions} readOnly={readOnly} people={people}
          card={askTarget && askTarget.request_id === settingsPerson.request_id && linkStatus(settingsPerson) === 'active' ? card : null}
          onClose={() => write({ settings: '' })} />
      )}
      <div className="bnf-advisor-views bnf-board-views" role="group" aria-label="Tab">
        <span className="bnf-advisor-views-label">Tab</span>
        {data.panes.map((entry) => (
          <button key={entry.key} type="button" className={cx('bnf-viewtab', entry.key === pane && 'bnf-viewtab-on')} aria-pressed={entry.key === pane}
            onClick={() => write({ pane: entry.key === 'intake' ? '' : entry.key })}>
            {entry.label}
            {entry.waiting + entry.in_cart > 0 ? ` · ${entry.waiting + entry.in_cart}` : ''}
          </button>
        ))}
        <span className="bnf-advisor-views-label">Show</span>
        {SHOWS.map((entry) => (
          <button key={entry.key} type="button" className={cx('bnf-viewtab', entry.key === show && 'bnf-viewtab-on')} aria-pressed={entry.key === show}
            onClick={() => write({ show: entry.key === 'all' ? '' : entry.key })}>
            {entry.label} · {data.counts[entry.key] ?? 0}
          </button>
        ))}
        {!readOnly && (
          <button type="button" className={cx('bnf-viewtab', editing && 'bnf-viewtab-on')} aria-pressed={editing} onClick={() => write({ edit: editing ? '' : '1' })}
            title="Type in answers read over the phone, as the client's or as ours">
            ✎ Edit mode
          </button>
        )}
      </div>
      {data.new.length > 0 && (
        <div className="rr-reqpage-new" role="status">
          <b>{data.new.length} new since your last look</b>
          <span> · {data.new.map((ref) => data.items.find((entry) => entry.ref === ref)?.label || ref).join(', ')}</span>
        </div>
      )}
      <div className="rr-reqpage">
        <div className="rr-reqpage-rail">
          <AskRail page={data} items={items} labels={labels} readOnly={readOnly} busy={busy} picked={picked} actions={railActions} mode={mode} />
        </div>
        <div className="rr-reqpage-cart">
          {editing && <EditMode deal={deal} pane={pane} page={data} onDone={() => write({ edit: '' })} />}
          {!editing && askTarget && <TheirForm dealId={deal.id} body={previewBody} who={who} frameRef={frameRef} />}
          {!editing && !askTarget && (
            <>
              {made && <LinkReady result={made} actions={actions} onDone={() => setMade(null)} />}
              {choosing && <ChooseWho deal={deal} count={choosing.length} busy={sender.isPending} onSend={(body) => send({ ids: choosing, new: body })} onCancel={() => setChoosing(null)} />}
              <GoingOut tray={tray.data} sections={meta?.tray_sections} readOnly={readOnly} busy={busy} result={result} onSend={send} onRemove={railActions.onRemove}
                onChooseWho={setChoosing} onDismiss={() => setResult(null)} />
              <OurRows page={data} labels={labels} picked={picked} onPick={setPicked} onEdit={railActions.onEdit} />
            </>
          )}
        </div>
        <div className="rr-reqpage-cards">
          {askTarget && !editing ? (
            <MarginColumn items={data.items} threads={data.threads} picked={picked} frameRef={frameRef} cardProps={cardProps}
              onPick={setPicked} onEdit={railActions.onEdit} onReview={() => onGo({ tab: 'review', view: 'queue', section: QUEUE_OF[pane] || 'intake' })} />
          ) : (
            <ItemCard {...cardProps} onClose={() => setPicked(null)} />
          )}
        </div>
      </div>
      {drawer && (
        <PeopleLinks requests={requests.data?.requests} meta={meta} actions={actions} readOnly={readOnly} onEdit={editPerson}
          onNew={() => {
            setDrawer(false);
            onNewLink();
          }}
          onClose={() => setDrawer(false)} />
      )}
    </div>
  );
}
