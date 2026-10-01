import { Component, type ErrorInfo, type ReactNode } from 'react';

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App error:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--background)] px-4">
          <div className="max-w-md w-full rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-lg">
            <h1 className="text-lg font-semibold text-[var(--foreground)]">Something went wrong</h1>
            <p className="text-sm text-[var(--muted)] mt-2">
              The dashboard could not load. Try a hard refresh (Ctrl+Shift+R) or sign in again.
            </p>
            <pre className="mt-4 text-xs text-red-700 bg-red-50 dark:bg-red-950/40 p-3 rounded-lg overflow-auto max-h-40">
              {this.state.error.message}
            </pre>
            <button
              type="button"
              className="mt-4 w-full py-2.5 rounded-xl bg-[var(--primary)] text-white text-sm font-semibold"
              onClick={() => window.location.assign('/login')}
            >
              Go to sign in
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
