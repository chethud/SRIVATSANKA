import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { KeyRound } from 'lucide-react';
import { BrandLogo } from '../components/BrandLogo';
import { LoadingScreen } from '../components/ui';
import { useAuth } from '../context/AuthContext';
import { isSupabaseAuth, supabase } from '../lib/supabase';

export default function ResetPasswordPage() {
  const {
    updatePassword,
    logout,
    loading: authLoading,
    isAuthenticated,
    passwordRecovery,
    usesSupabase,
  } = useAuth();
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [checkingLink, setCheckingLink] = useState(true);
  const [linkReady, setLinkReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function checkSession() {
      if (!isSupabaseAuth || !supabase) {
        if (!cancelled) {
          setLinkReady(false);
          setCheckingLink(false);
        }
        return;
      }
      const { data } = await supabase.auth.getSession();
      if (cancelled) return;
      setLinkReady(Boolean(data.session) || passwordRecovery);
      setCheckingLink(false);
    }

    void checkSession();
    return () => {
      cancelled = true;
    };
  }, [passwordRecovery]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Use at least 8 characters for the new password.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      await updatePassword(password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update password');
    } finally {
      setSubmitting(false);
    }
  }

  if (authLoading || checkingLink) {
    return <LoadingScreen text="Opening reset link…" />;
  }

  if (!usesSupabase) {
    return (
      <AuthShell title="Reset password">
        <p className="text-sm text-[var(--muted)]">
          Email password reset needs Supabase sign-in. Ask an admin to update the server password.
        </p>
        <Link to="/login" className="mt-4 inline-block text-sm font-semibold text-[var(--primary)] hover:underline">
          Back to sign in
        </Link>
      </AuthShell>
    );
  }

  if (!linkReady && !isAuthenticated) {
    return (
      <AuthShell title="Reset password">
        <p className="text-sm text-[var(--muted)]">
          This reset link is missing or expired. Request a new one from the sign-in page.
        </p>
        <Link to="/login" className="mt-4 inline-block text-sm font-semibold text-[var(--primary)] hover:underline">
          Back to sign in
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Choose a new password" subtitle="Enter a new password for your account">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="new-password" className="block text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-1.5">
            New password
          </label>
          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/30"
            required
            minLength={8}
          />
        </div>
        <div>
          <label htmlFor="confirm-password" className="block text-xs font-medium text-[var(--muted)] uppercase tracking-wide mb-1.5">
            Confirm password
          </label>
          <input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/30"
            required
            minLength={8}
          />
        </div>
        {error && (
          <p className="text-sm text-[var(--danger)] bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 rounded-lg px-3 py-2">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 rounded-xl bg-[var(--primary)] text-white font-semibold text-sm hover:bg-[var(--primary-hover)] disabled:opacity-50 transition-colors"
        >
          {submitting ? 'Saving…' : 'Update password'}
        </button>
        <button
          type="button"
          onClick={() => {
            void (async () => {
              await logout();
              navigate('/login', { replace: true });
            })();
          }}
          className="w-full text-sm font-medium text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          Cancel and sign in
        </button>
      </form>
    </AuthShell>
  );
}

function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background)] px-4">
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <BrandLogo variant="horizontal" className="max-w-[240px] mx-auto" />
        </div>
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-xl)] shadow-[var(--shadow-md)] p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2.5 rounded-xl bg-[var(--primary)]/10 text-[var(--primary)]">
              <KeyRound size={22} />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-[var(--foreground)]">{title}</h1>
              {subtitle && <p className="text-sm text-[var(--muted)] mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
