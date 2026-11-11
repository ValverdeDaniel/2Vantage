import { Component } from 'react';
import InlineError from './InlineError';

/**
 * Catches a render error below it and shows it with Try again instead of a blank page.
 *   resetKey: when it changes (e.g. the route or tab), the boundary clears itself
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
    const isChunkError = /dynamically imported module|Importing a module script failed/i.test(error.message || '');
    return (
      <InlineError
        title={isChunkError ? 'A newer version of 2Vantage is available. Reload the page.' : 'Something went wrong here.'}
        error={isChunkError ? null : error}
        onRetry={isChunkError ? () => window.location.reload() : this.reset}
      />
    );
  }
}
