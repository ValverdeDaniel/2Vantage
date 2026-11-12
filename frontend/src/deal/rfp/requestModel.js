// The request card's words and write bodies, pure (plan.md §8.12; K17–K29; old CarriersTab.jsx RequestPanel at
// 891f1b3). Vocabularies come from /api/meta/ `rfp` (rule 1); the server checks every value.
import { formatDate } from '../../lib/format';
import { optimisticTicks } from './packet/packetModel';

const plural = (count, noun) => `${count} ${noun}${count === 1 ? '' : 's'}`;

/** The collapsed card's one line (K28): "Direct to carriers · 3 carriers · due Jan 15, 2027". */
export function requestSummary(request, routes) {
  const route = (routes || []).find((entry) => entry.key === request.route);
  return [
    route?.long || '',
    plural((request.carriers || []).length, 'carrier'),
    request.due_date ? `due ${formatDate(request.due_date)}` : '',
  ]
    .filter(Boolean)
    .join(' · ');
}

/** "Large group (51+) · 60 enrolled", with where an estimate came from (K17, K18). */
export function bandWords(band) {
  if (band.count == null) return `${band.label} · no enrolled count yet`;
  const estimate = band.estimate ? ` (an estimate: ${band.from})` : '';
  return `${band.label} · ${band.count} enrolled${estimate}`;
}

/** The census line's readiness colour (K8; old readinessClass): green from 90, amber from 70, else rose. */
export function readinessClass(pct) {
  if (pct >= 90) return 'bb-green';
  if (pct >= 70) return 'bb-amber';
  return 'bb-rose';
}

/** With no census, where the band's count came from instead (K8). */
export function noCensusWords(band) {
  if (band.count == null) return 'no census yet, and no enrolled count anywhere';
  return `no census yet — the band's ${band.count} enrolled come from ${band.from || 'intake'}`;
}

/** A carrier chip's tooltip (K23): why it is dimmed, its note, the lines it quotes here. */
export function chipTitle(chip) {
  return [chip.reason, chip.note, (chip.line_labels || []).join(', ')].filter(Boolean).join(' · ');
}

/** The body a route chip sends (K20): null when it lands back on the band's route; nothing when already picked. */
export function routeBody(key, request) {
  if (key === request.route) return null;
  return { route: key === request.route_default ? null : key };
}

/** The body a funding or carrier chip sends (K21, K25): what the click changes, never the whole list. */
export function toggleBody(field, key, picked) {
  return { [field]: (picked || []).includes(key) ? { remove: [key] } : { add: [key] } };
}

function toggled(list, change, order) {
  const wanted = new Set([...(list || []), ...(change.add || [])]);
  for (const key of change.remove || []) wanted.delete(key);
  return order.filter((key) => wanted.has(key));
}

/** The page as the click leaves it, before the server answers (K.6: optimistic toggles). */
export function optimistic(page, body, fundingOrder) {
  const request = { ...page.request };
  let { carriers } = page;
  if (body.carriers) {
    request.carriers = toggled(request.carriers, body.carriers, carriers.map((chip) => chip.key));
    const picked = new Set(request.carriers);
    carriers = carriers.map((chip) => ({ ...chip, selected: picked.has(chip.key) }));
  }
  if (body.funding) {
    request.funding = toggled(request.funding, body.funding, fundingOrder);
    request.funding_default = false;
  }
  if ('route' in body) {
    request.route = body.route || request.route_default;
    request.route_stored = body.route || '';
  }
  for (const key of ['other_carriers', 'due_date', 'notes']) {
    if (key in body) request[key] = body[key] ?? '';
  }
  const packet = 'include' in body ? optimisticTicks(page.packet, body.include) : page.packet;
  return { ...page, request, carriers, packet };
}

/** A write's answer into the page: the blocks the request and packet cards redraw. */
export function adopt(page, answer) {
  const packet = answer.packet ?? page.packet;
  return { ...page, request: answer.request, carriers: answer.carriers, packet, done: answer.done };
}
