import { useTeam } from '../../../api/proposalFirm';

/*
 * Who is on this client's team (plan.md §8.14; J43; the old PresentationPagesCard's team block at 891f1b3): a tick per
 * person on the firm's team. Until a deal picks, everyone "on every proposal" is ticked (`team` null); a tick writes
 * the deal's own list (`team`, in the firm's order), and the team and bio pages print those people only.
 */
export default function TeamPicks({ picks, busy, onSet }) {
  const team = useTeam().data ?? [];
  if (!team.length) return null;
  const picked = Array.isArray(picks) ? picks : team.filter((member) => member.on_by_default).map((member) => member.id);
  const toggle = (id, on) => {
    const next = on ? [...picked, id] : picked.filter((other) => other !== id);
    onSet('team', team.filter((member) => next.includes(member.id)).map((member) => member.id));
  };
  return (
    <div className="bnf-present-block">
      <div className="bnf-present-head">Who is on this client&apos;s team</div>
      <div className="bnf-present-checks">
        {team.map((member) => (
          <label key={member.id} className="bnf-output-check">
            <input
              type="checkbox"
              checked={picked.includes(member.id)}
              disabled={busy}
              onChange={(event) => toggle(member.id, event.target.checked)}
            />
            {member.name}
            {member.group ? ` (${member.group})` : ''}
          </label>
        ))}
      </div>
    </div>
  );
}
