import { photoUrl } from '../../../api/proposalFirm';

const FIELDS = [
  ['name', 'Name', 120],
  ['title', 'Title', 120],
  ['group', 'Role on the client’s team', 80],
  ['phone', 'Phone', 50],
  ['email', 'Email', 254],
];

/*
 * One person on the firm's team in the Firm pages drawer (plan.md §8.14; J155; the old FirmPagesPanel's person and
 * PersonPhoto at 891f1b3, same words and classes): the photo (Upload / Replace / Remove; stored re-encoded, without
 * metadata), each field saved on leaving it, the bio, "On every proposal unless a deal picks its own team", and
 * Remove from the team. `writes` is useTeamWrites(); `run` toasts a refusal.
 */
export default function FirmPerson({ member, limits, writes, run }) {
  const save = (key) => (event) => {
    const value = event.target.value.trim();
    if (value !== (member[key] ?? '')) run(writes.save.mutateAsync({ id: member.id, [key]: value }));
  };
  const remove = () => {
    if (window.confirm(`Remove ${member.name} from the team, on every proposal?`)) run(writes.remove.mutateAsync(member.id));
  };
  const busy = writes.photo.isPending || writes.noPhoto.isPending;
  return (
    <div className="bnf-firm-person">
      <div className="bnf-firm-photo">
        {member.has_photo ? (
          <img src={photoUrl(member.id, member.photo_version)} alt={member.name} />
        ) : (
          <span className="bnf-firm-photo-none">No photo</span>
        )}
        <label className="btn btn-secondary btn-sm" aria-busy={busy || undefined}>
          {member.has_photo ? 'Replace' : 'Upload'}
          <input
            type="file"
            accept=".png,.jpg,.jpeg"
            hidden
            disabled={busy}
            aria-label={`Photo of ${member.name}`}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) run(writes.photo.mutateAsync({ id: member.id, file }));
              event.target.value = '';
            }}
          />
        </label>
        {member.has_photo && (
          <button type="button" className="bnf-override-link" disabled={busy} onClick={() => run(writes.noPhoto.mutateAsync(member.id))}>
            Remove
          </button>
        )}
      </div>
      <div className="bnf-firm-person-fields">
        {FIELDS.map(([key, label, max]) => (
          <label key={key}>
            <span>{label}</span>
            <input type="text" maxLength={max} defaultValue={member[key]} onBlur={save(key)} />
          </label>
        ))}
        <label className="bnf-firm-person-bio">
          <span>Bio</span>
          <textarea rows={3} maxLength={limits.bio} defaultValue={member.bio} onBlur={save('bio')} />
        </label>
        <label className="bnf-output-check">
          <input
            type="checkbox"
            checked={member.on_by_default}
            onChange={(event) => run(writes.save.mutateAsync({ id: member.id, on_by_default: event.target.checked }))}
          />
          On every proposal unless a deal picks its own team
        </label>
        <button type="button" className="bnf-override-link" onClick={remove}>
          Remove from the team
        </button>
      </div>
    </div>
  );
}
