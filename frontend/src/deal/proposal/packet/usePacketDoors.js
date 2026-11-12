import { useIsMutating, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { downloadFile } from '../../../lib/download';
import { errorText } from '../../../lib/errors';
import { useToast } from '../../../ui/useToast';

const SETTLE_MS = 15000;

/** A refusal's own sentence (409 {detail, blockers}), else the usual words. */
export function refusalText(error, fallback) {
  const detail = error?.response?.data?.detail;
  return typeof detail === 'string' && detail ? detail : errorText(error, { fallback });
}

/*
 * The packet card's doors (plan.md §8.15; J96, J97, J101; the old ProposalPacketCard's `deliver`): one click, one
 * file — a second click while it builds gets a toast — and each door has its own guard, so a slow PDF never blocks
 * another. Every door first waits for the writes still saving anywhere on the page (`useIsMutating`, J101), so a value
 * just typed is in the file. `saving` greys Issue meanwhile.
 */
export default function usePacketDoors() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const saving = useIsMutating() > 0;
  const working = useRef({});
  const [busy, setBusy] = useState({});

  async function settle() {
    const until = Date.now() + SETTLE_MS;
    while (queryClient.isMutating() > 0 && Date.now() < until) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }

  async function deliver(kind, send, fallback) {
    if (working.current[kind]) {
      toast.info('Already working on that — one moment.');
      return undefined;
    }
    working.current[kind] = true;
    setBusy((now) => ({ ...now, [kind]: true }));
    try {
      await settle();
      return await send();
    } catch (error) {
      toast.error(refusalText(error, fallback));
      return undefined;
    } finally {
      working.current[kind] = false;
      setBusy((now) => ({ ...now, [kind]: false }));
    }
  }

  function download(kind, url, fallback, params) {
    return deliver(kind, () => downloadFile(url, { params }), fallback);
  }

  return { saving, busy, deliver, download };
}
