import { useMeta } from '../../api/meta';
import { claudeDoor } from './door';
import { tabKinds } from './drawerWords';

/*
 * "＋ Add quotes" (plan.md §8.14, §8.17; F96, D37; the old ComparisonGrid's button): the board's own door to Work with
 * Claude, opened on carrier quotes; files drop on the drawer (the board keeps no drop zone of its own, DROP-1). Hidden
 * without Claude set up (D26). "＋ Add SBCs" joins with the SBC reader (slice 22).
 */
export default function AddQuotesButton({ primary = false }) {
  const { data: meta } = useMeta();
  if (!meta?.ai) return null;
  return (
    <button
      type="button"
      className={`btn btn-sm ${primary ? 'btn-primary' : 'btn-secondary'}`}
      title="Drop carrier quotes into Claude over this page"
      onClick={() => claudeDoor.open(tabKinds(meta, 'advisor')[0] || '')}
    >
      ＋ Add quotes
    </button>
  );
}

export function AddSbcsButton() {
  const { data: meta } = useMeta();
  if (!(meta?.ai?.targets || []).some((target) => target.key === 'sbc')) return null;
  return (
    <button
      type="button"
      className="btn btn-secondary btn-sm"
      title="Read each plan's Summary of Benefits and Coverage into the plans on this deal — plan design only, never a rate, reviewed before anything changes"
      onClick={() => claudeDoor.open('sbc')}
    >
      ＋ Add SBCs
    </button>
  );
}
