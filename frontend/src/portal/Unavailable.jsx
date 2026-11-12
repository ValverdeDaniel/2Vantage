/*
 * A link that does not open (plan.md §8.20; L107, L136): the old "Link unavailable" card (`bb-portal-center`) with
 * the server's sentence, and the agency's phone and email so the person can ask for a new link (L107, Ch. 11c: never
 * an owner). The moved page (/b/, L136) is the same card with its own title.
 */
export default function Unavailable({ title = 'Link unavailable', sentence, agency }) {
  const reach = [agency?.phone, agency?.email].filter(Boolean);
  return (
    <div className="bb-portal-card bb-portal-center">
      <div className="bb-portal-thanks-title">{title}</div>
      <div className="bb-subtitle">{sentence}</div>
      {reach.length > 0 && (
        <div className="bb-subtitle">
          {agency.name ? `${agency.name}: ` : ''}
          {agency.phone && <a href={`tel:${agency.phone}`}>{agency.phone}</a>}
          {agency.phone && agency.email && ' · '}
          {agency.email && <a href={`mailto:${agency.email}?subject=A new link, please`}>{agency.email}</a>}
        </div>
      )}
    </div>
  );
}
