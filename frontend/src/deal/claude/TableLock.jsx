import { useQuery } from '@tanstack/react-query';
import { aiKey } from '../../api/ai';
import api from '../../api/client';
import { useMeta } from '../../api/meta';
import LockSwitch from './LockSwitch';

/*
 * The lock switch on a plan table's toolbar (plan.md §8.14; F113, D104; the old ClaudeLockSwitch `compact`): the same
 * switch as the drawer's, reading the deal's AI state the drawer polls (it adds no poller of its own). Hidden without
 * Claude set up (D26).
 */
export default function TableLock({ dealId }) {
  const { data: meta } = useMeta();
  const state = useQuery({
    queryKey: aiKey(dealId),
    queryFn: async () => (await api.get(`deals/${dealId}/ai/`)).data,
    enabled: Boolean(meta?.ai),
  });
  if (!meta?.ai || !state.data?.claude) return null;
  return <LockSwitch dealId={dealId} lock={state.data.lock} compact />;
}
