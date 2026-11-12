import { Link } from 'react-router';

/** Any other address (plan.md §8.1): "Page not found" with a way back to the home page, on the old home header. */
export default function NotFoundPage() {
  return (
    <div className="bb-dash">
      <div className="bb-dash-header">
        <div>
          <div className="bb-title">Page not found</div>
          <div className="bb-subtitle">The address may be mistyped, or the page may have moved.</div>
        </div>
        <Link to="/" className="btn btn-primary bb-new-btn">
          Go to the home page
        </Link>
      </div>
    </div>
  );
}
