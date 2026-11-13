// The sidebar nav's badges (A21, L13, H9; old CaseNav at 891f1b3), from the shell's `journey/` read: a plain count, or
// on Review & requests three tones — to review (violet), waiting on the client (amber), missing (rose) — each saying
// what it counts; a "?" for the client's open questions; the violet ↩ beside a section whose client answers or
// questions wait to be reviewed. Its own badge stays beside them.

const TONES = [
  ['review', 'violet', 'to review: their answers and questions, and AI reads'],
  ['waiting', 'amber', 'waiting on the client: still typing, or sent back to them'],
  ['missing', 'rose', 'missing: required and still blank, asked or not'],
];

function Question({ count }) {
  if (!count) return null;
  const words = `${count} question${count === 1 ? '' : 's'} from the client waiting on our answer`;
  return (
    <span className="bb-nav-question" title={words} aria-label={words}>
      ?
    </span>
  );
}

function Toned({ badge }) {
  return (
    <span className="bb-nav-badges">
      <Question count={badge.questions || 0} />
      {TONES.filter(([key]) => badge[key] > 0).map(([key, tone, words]) => (
        <span
          key={key}
          className={`bb-nav-badge bb-nav-badge-${tone}`}
          title={`${badge[key]} ${words}`}
          aria-label={`${badge[key]} ${words}`}
        >
          {badge[key]}
        </span>
      ))}
    </span>
  );
}

/** The badges after one nav item's label; nothing while the shell's read has not landed. */
export default function NavBadges({ tab, badges }) {
  if (!badges) return null;
  const badge = badges[tab];
  if (badge && typeof badge === 'object') return <Toned badge={badge} />;
  const plain = badge > 0 ? <span className="bb-nav-badge">{badge}</span> : null;
  const back = badges.returned?.[tab] ? (
    <span className="bb-nav-return" title="The client's answers or questions wait to be reviewed">
      ↩
    </span>
  ) : null;
  const asked = badges.asked?.[tab] || 0;
  if (!back && !asked) return plain;
  return (
    <span className="bb-nav-badges">
      <Question count={asked} />
      {back}
      {plain}
    </span>
  );
}
