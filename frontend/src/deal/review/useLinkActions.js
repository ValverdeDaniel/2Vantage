import { useQueryClient } from '@tanstack/react-query';
import { createElement, useState } from 'react';
import { revertActivity } from '../../api/deals';
import { reviewKey, useCloseRequest, useLinkAction } from '../../api/review';
import { errorText } from '../../lib/errors';
import { useToast } from '../../ui/useToast';
import copyText from './clipboard';
import { linkUrl } from './reviewModel';

/*
 * What a request card's buttons do (L8, L60, L64, L70, L71), in the old words (891f1b3 `DealReviewTab.jsx` `copy`,
 * `LinkSettingsCard.jsx` `switchLink`): Copy link copies first and then marks the link sent — copying is the send
 * (OQ82); Turn off, Turn back on and Close… say what they did and offer Undo (Revert of their Activity row); a new
 * PIN is held here to show once. Every refusal is the server's sentence.
 */
const whose = (person) => (person.name ? `${person.name}’s` : 'The private');

export default function useLinkActions(dealId) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const act = useLinkAction(dealId);
  const closer = useCloseRequest(dealId);
  const [pins, setPins] = useState({}); // {link id: a new PIN}, shown this once

  async function undo(activityId, words) {
    try {
      await revertActivity(activityId);
      toast.success(words);
    } catch (error) {
      toast.error(errorText(error));
    }
    queryClient.invalidateQueries({ queryKey: reviewKey(dealId, 'board') });
  }

  function said(message, activityId, undone) {
    if (!activityId) {
      toast.success(message);
      return;
    }
    const button = createElement(
      'button',
      { type: 'button', className: 'bnf-linklike', onClick: () => undo(activityId, undone) },
      'Undo',
    );
    toast.success(createElement('span', null, message, ' · ', button), { duration: 10000 });
  }

  async function run(person, action, extra = {}) {
    try {
      return await act.mutateAsync({ linkId: person.link_id, action, ...extra });
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not change that link.' }));
      return null;
    }
  }

  async function copyLink(person) {
    const url = linkUrl(person.path, window.location.origin);
    if (!(await copyText(url))) {
      toast.error(`Copy blocked by the browser — select the link and copy it by hand: ${url}`, { duration: 0 });
      return false;
    }
    if (person.sent) {
      toast.success('Copied');
      return true;
    }
    const answer = await run(person, 'mark_sent', { copied: true });
    if (answer) toast.success('Copied — marked as sent');
    return Boolean(answer);
  }

  async function markSent(person, back = false) {
    const answer = await run(person, back ? 'unsend' : 'mark_sent');
    if (answer?.activity_id) toast.success(back ? 'Put back to not sent yet' : 'Marked as sent');
  }

  async function extend(person) {
    const answer = await run(person, 'extend');
    if (answer?.activity_id) said(`${whose(person)} link lives its own life again from today`, answer.activity_id, 'Undone');
  }

  async function revoke(person) {
    const answer = await run(person, 'revoke');
    if (answer?.activity_id) {
      said(
        `${whose(person)} link is off: what they said stays, and what it asked reads missing`,
        answer.activity_id,
        'Undone — the link is back on',
      );
    }
  }

  async function restore(person) {
    const answer = await run(person, 'restore');
    if (answer?.activity_id) {
      said(`${whose(person)} link is back on: the same URL opens again`, answer.activity_id, 'Undone — the link is off');
    }
  }

  async function newPin(person) {
    const answer = await run(person, 'new_pin');
    if (answer?.pin) setPins((now) => ({ ...now, [person.link_id]: answer.pin }));
  }

  async function close(request, reason) {
    try {
      const answer = await closer.mutateAsync({ requestId: request.id, reason });
      if (answer.activity_id) said('Request closed: every link on it stops working', answer.activity_id, 'Undone — the request is open again');
    } catch (error) {
      toast.error(errorText(error, { fallback: 'Could not close the request.' }));
    }
  }

  return {
    busy: act.isPending || closer.isPending,
    pins,
    copyLink,
    markSent,
    extend,
    revoke,
    restore,
    newPin,
    close,
  };
}
