import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { KeyRound, Lock } from 'lucide-react';
import { BrandLogo } from '../components/BrandLogo';
import { LoadingScreen } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { BRAND_NAME } from '../brand';

export default function LoginPage() {
  const {
    login,
    requestPasswordReset,
    isAuthenticated,
    loading: authLoading,
    usesSupabase,
    passwordRecovery,
  } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/';

  const [mode, setMode] = useState<'signin' | 'forgot'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (authLoading) {
    return <LoadingScreen text="Checking sign-in…" />;
  }

  if (passwordRecovery) {
    return <Navigate to="/reset-password" replace />;
  }

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function handleSignIn(e: FormEvent) {
    e.preventDefault();
    setError('');
    setInfo('');
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleForgot(e: FormEvent) {
    e.preventDefault();
    setError('');
    setInfo('');
    setSubmitting(true);
    try {
      await requestPasswordReset(email.trim());
      setInfo('Check your email for a password reset link. It may take a minute to arrive.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send reset email');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)] px-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <BrandLogo variant="horizontal" className="max-w-[240px] mx-auto" />
        </div>
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-xl)] shadow-[var(--shadow-md)] p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2.5 rounded-xl bg-[var(--primary)]/10 text-[var(--primary)]">
              {mode === 'forgot' ? <KeyRound size={22} /> : <Lock size={22} />}
            </div>
            <div>
              <h1 className="text-xl font-semibold text-[var(--foreground)]">
                {mode === 'forgot' ? 'Reset password' : 'Sign in'}
              </h1>
              <p className="text-sm text-[var(--muted)] mt-0.5">
                {mode === 'forgot'
                  ? usesSupabase
                    ? 'We will email you a reset link'
                    : 'Password reset help'
                  : `${BRAND_NAME} dashboard`}
              </p>
            </div>
          </div>

          {mode === 'signin' ? (
            <form onSubmit={handleSignIn} className="space-y-4">
              <div>
                <label htmlFor="login-id" className="block text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-1.5">
                  {usesSupabase ? 'Email' : 'Username / ID'}
                </label>
                <input
                  id="login-id"
                  type={usesSupabase ? 'email' : 'text'}
                  autoComplete={usesSupabase ? 'email' : 'username'}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/30"
                  placeholder={usesSupabase ? 'you@example.com' : 'Admin'}
                  required
                />
              </div>
              <div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <label htmlFor="password" className="block text-xs font-medium text-[var(--muted)] uppercase tracking-wide">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setMode('forgot');
                      setError('');
                      setInfo('');
                    }}
                    className="text-xs font-semibold text-[var(--primary)] hover:underline"
                  >
                    Forgot password?
                  </button>
                </div>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/30"
                  required
                />
              </div>
              {error && (
                <p className="text-sm text-[var(--danger)] bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}
              <button
                type="submit"
                disabled={submitting || authLoading}
                className="w-full py-2.5 rounded-xl bg-[var(--primary)] text-white font-semibold text-sm hover:bg-[var(--primary-hover)] disabled:opacity-50 transition-colors"
              >
                {submitting ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          ) : !usesSupabase ? (
            <div className="space-y-3">
              <p className="text-sm text-[var(--muted)]">
                This dashboard runs on AWS with a single Admin sign-in. Password reset by email is not enabled.
              </p>
              <p className="text-xs text-[var(--muted)]">
                Ask an admin to update <code className="text-[var(--foreground)]">DASHBOARD_PASSWORD</code> in the
                EC2 <code className="text-[var(--foreground)]">whatsapp/.env</code> file, then restart{" "}
                <code className="text-[var(--foreground)]">kannans-backend</code>.
              </p>
              <button
                type="button"
                onClick={() => {
                  setMode('signin');
                  setError('');
                  setInfo('');
                }}
                className="w-full text-sm font-medium text-[var(--muted)] hover:text-[var(--foreground)]"
              >
                Back to sign in
              </button>
            </div>
          ) : (
            <form onSubmit={handleForgot} className="space-y-4">
              <div>
                <label htmlFor="reset-email" className="block text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-1.5">
                  Email
                </label>
                <input
                  id="reset-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/30"
                  placeholder="you@example.com"
                  required
                />
              </div>
              {info && (
                <p className="text-sm text-[var(--primary)] bg-[var(--primary-light)] border border-[var(--border)] rounded-lg px-3 py-2">
                  {info}
                </p>
              )}
              {error && (
                <p className="text-sm text-[var(--danger)] bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}
              <button
                type="submit"
                disabled={submitting || authLoading}
                className="w-full py-2.5 rounded-xl bg-[var(--primary)] text-white font-semibold text-sm hover:bg-[var(--primary-hover)] disabled:opacity-50 transition-colors"
              >
                {submitting ? 'Sending…' : 'Send reset link'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('signin');
                  setError('');
                  setInfo('');
                }}
                className="w-full text-sm font-medium text-[var(--muted)] hover:text-[var(--foreground)]"
              >
                Back to sign in
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
