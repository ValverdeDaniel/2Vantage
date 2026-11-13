// The link settings card's and People & links' pure helpers (plan.md §8.8; L38, L39; old 891f1b3
// `LinkSettingsCard.jsx`, `RequestPeople.jsx`). The server says each link's state; these group and word it.

/** Every link ever made, from the request rows, each with its request's id, asks and message: [person]. */
export function peopleOf(requests) {
  return (requests || []).flatMap((request) =>
    request.recipients.map((person) => ({
      ...person,
      request_id: request.id,
      asks: request.asks,
      message: request.message,
      request_state: request.state,
      closed: Boolean(request.closed_at),
    })),
  );
}

/** One link's standing on the card: active, revoked (turned off), expired (ran out) or closed (its request). */
export function linkStatus(person) {
  if (person.closed) return 'closed';
  if (person.revoked) return 'revoked';
  if (person.expired) return 'expired';
  return 'active';
}

/** The card's words for whether it is on (old `LinkStatus`). */
export function statusNote(person, name) {
  const status = linkStatus(person);
  if (status === 'revoked') {
    return person.can_restore
      ? 'On: the same link opens again, with its own life from now.'
      : `It is past its 30-day limit, so it cannot open again: make a new link${person.name ? ` for ${name}` : ''}.`;
  }
  if (status === 'expired') {
    return person.can_extend
      ? 'It ran out. Pick a date below, or Extend, and the same link opens again.'
      : `It ran out and is past its 30-day limit, so it cannot open again: make a new link${person.name ? ` for ${name}` : ''}.`;
  }
  if (status === 'closed') return 'Its request was closed, so this link no longer opens.';
  return 'Off: the link stops opening now. What they told us stays, and what it asked reads missing until it is back on.';
}

/** 'YYYY-MM-DD' of an ISO time on the reader's own calendar. */
export function dayOf(iso) {
  if (!iso) return '';
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${when.getFullYear()}-${pad(when.getMonth() + 1)}-${pad(when.getDate())}`;
}

/** The day before a YYYY-MM-DD: the last day a reminder to nudge may be set (it is before the link runs out). */
export function dayBefore(day) {
  if (!day) return '';
  const when = new Date(`${day}T12:00:00`);
  when.setDate(when.getDate() - 1);
  return dayOf(when.toISOString());
}

/** "Priya’s What they see and Expires": someone else's settings going with this update. */
export function othersWaiting(settings, linkId, people) {
  return Object.entries(settings || {})
    .filter(([id]) => Number(id) !== linkId)
    .map(([id, own]) => {
      const who = (people || []).find((person) => person.link_id === Number(id))?.name || 'Someone else';
      const what = [
        'blank' in own ? 'What they see' : '',
        'expires_on' in own ? 'Expires' : '',
        'nudge_on' in own ? 'Remind me to nudge' : '',
      ]
        .filter(Boolean)
        .join(' and ');
      return `${who}’s ${what}`;
    });
}
