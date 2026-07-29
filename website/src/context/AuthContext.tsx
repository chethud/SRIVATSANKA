import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { getAuthToken, login as apiLogin, setAuthToken, verifySession } from '../api/client';
import { isSupabaseAuth, supabase } from '../lib/supabase';

interface AuthState {
  token: string | null;
  username: string | null;
  loading: boolean;
  login: (emailOrUsername: string, password: string) => Promise<void>;
  logout: () => void;
  requestPasswordReset: (email: string) => Promise<void>;
  updatePassword: (password: string) => Promise<void>;
  clearPasswordRecovery: () => void;
  isAuthenticated: boolean;
  usesSupabase: boolean;
  passwordRecovery: boolean;
}

const AuthContext = createContext<AuthState | null>(null);

function applySupabaseSession(
  session: { access_token: string; user: { email?: string | null; id: string } } | null,
  setToken: (t: string | null) => void,
  setUsername: (u: string | null) => void,
  setAuthenticated: (v: boolean) => void,
) {
  if (session?.access_token) {
    setAuthToken(session.access_token);
    setToken(session.access_token);
    setUsername(session.user.email ?? session.user.id);
    setAuthenticated(true);
    return;
  }
  setAuthToken(null);
  setToken(null);
  setUsername(null);
  setAuthenticated(false);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [passwordRecovery, setPasswordRecovery] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        if (isSupabaseAuth && supabase) {
          const { data } = await supabase.auth.getSession();
          if (cancelled) return;
          if (data.session) {
            applySupabaseSession(data.session, setToken, setUsername, setAuthenticated);
            void verifySession()
              .then((me) => {
                if (!cancelled) setUsername(me.username);
              })
              .catch(async (err) => {
                const msg = err instanceof Error ? err.message : '';
                if (!cancelled && supabase && msg.includes('Session expired')) {
                  await supabase.auth.signOut();
                  applySupabaseSession(null, setToken, setUsername, setAuthenticated);
                }
              });
          } else {
            applySupabaseSession(null, setToken, setUsername, setAuthenticated);
          }
          return;
        }

        const t = getAuthToken();
        if (!t) return;
        setToken(t);
        setAuthenticated(true);
        verifySession()
          .then((me) => {
            if (!cancelled) setUsername(me.username);
          })
          .catch(() => {
            if (!cancelled) {
              setAuthToken(null);
              setToken(null);
              setUsername(null);
              setAuthenticated(false);
            }
          });
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    bootstrap();

    if (isSupabaseAuth && supabase) {
      const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
        if (event === 'PASSWORD_RECOVERY') {
          setPasswordRecovery(true);
        }
        if (session?.access_token) {
          applySupabaseSession(session, setToken, setUsername, setAuthenticated);
          return;
        }
        if (event === 'SIGNED_OUT') {
          setPasswordRecovery(false);
          applySupabaseSession(null, setToken, setUsername, setAuthenticated);
        }
      });
      return () => {
        cancelled = true;
        listener.subscription.unsubscribe();
      };
    }

    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (emailOrUsername: string, password: string) => {
    if (isSupabaseAuth && supabase) {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: emailOrUsername.trim(),
        password,
      });
      if (error) throw new Error(error.message);
      const session = data.session;
      if (!session?.access_token) throw new Error('Sign in failed — no session returned');
      setPasswordRecovery(false);
      applySupabaseSession(session, setToken, setUsername, setAuthenticated);
      void verifySession()
        .then((me) => setUsername(me.username))
        .catch(() => {
          /* Dashboard loads; API errors show in the data banner */
        });
      return;
    }

    const res = await apiLogin(emailOrUsername, password);
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUsername(res.username);
    setAuthenticated(true);
  }, []);

  const requestPasswordReset = useCallback(async (email: string) => {
    if (!isSupabaseAuth || !supabase) {
      throw new Error(
        'Email password reset needs Supabase sign-in. Ask your admin to update the dashboard password on the server.',
      );
    }
    const redirectTo = `${window.location.origin}/reset-password`;
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo });
    if (error) throw new Error(error.message);
  }, []);

  const updatePassword = useCallback(async (password: string) => {
    if (!isSupabaseAuth || !supabase) {
      throw new Error('Password update is only available with Supabase sign-in.');
    }
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw new Error(error.message);
    setPasswordRecovery(false);
  }, []);

  const clearPasswordRecovery = useCallback(() => {
    setPasswordRecovery(false);
  }, []);

  const logout = useCallback(async () => {
    if (isSupabaseAuth && supabase) {
      await supabase.auth.signOut();
    }
    setPasswordRecovery(false);
    setAuthToken(null);
    setToken(null);
    setUsername(null);
    setAuthenticated(false);
  }, []);

  const value = useMemo(
    () => ({
      token,
      username,
      loading,
      login,
      logout,
      requestPasswordReset,
      updatePassword,
      clearPasswordRecovery,
      isAuthenticated: isSupabaseAuth ? authenticated : Boolean(token),
      usesSupabase: isSupabaseAuth,
      passwordRecovery,
    }),
    [
      token,
      username,
      loading,
      login,
      logout,
      requestPasswordReset,
      updatePassword,
      clearPasswordRecovery,
      authenticated,
      passwordRecovery,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
