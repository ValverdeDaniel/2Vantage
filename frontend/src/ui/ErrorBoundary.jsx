import { Component } from 'react';

const CHUNK_ERROR = /dynamically imported module|Importing a module script failed/i;

/**
 * Catches a render error below it and shows the old crash card (`app-crash`) instead of a blank page: the message,
 * Try again (renders the part again) and Reload the page. The error still goes to the console.
 *   resetKey: when it changes (the route or the tab), the boundary clears itself
 *   fallback: optional ({error, reset}) => node
 */
export default class ErrorBoundary extends Component {
  state = { error: null, resetKey: undefined };

  static getDerivedStateFromError(error) {
    return { error };
  }

  static getDerivedStateFromProps(props, state) {
    if (props.resetKey !== state.resetKey) return { error: null, resetKey: props.resetKey };
    return null;
  }

  componentDidCatch(error, info) {
    console.error('Render error', error, info?.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    if (this.props.fallback) return this.props.fallback({ error, reset: this.reset });
    const stale = CHUNK_ERROR.test(error.message || '');
    return (
      <div className="app-crash" role="alert">
        <div className="app-crash-title">
          {stale ? 'A newer version of 2Vantage is available.' : 'This screen hit an error'}
        </div>
        {!stale && <div className="app-crash-msg">{String(error.message || error)}</div>}
        <p className="app-crash-hint">
          {stale
            ? 'Reload the page to open it.'
            : 'Nothing you did caused this. Other screens still work — use the navigation to move on, or reload to start fresh.'}
        </p>
        {!stale && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={this.reset}>
            Try again
          </button>
        )}{' '}
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => window.location.reload()}>
          Reload the page
        </button>
      </div>
    );
  }
}
