import { Link } from 'react-router';
import Button from '../../ui/Button';
import EmptyState from '../../ui/EmptyState';

export default function NotFoundPage() {
  return (
    <EmptyState
      title="Page not found"
      action={
        <Button as={Link} to="/" variant="primary">
          Go to the dashboard
        </Button>
      }
    >
      The address may be mistyped, or the page may have moved.
    </EmptyState>
  );
}
