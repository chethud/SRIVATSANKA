import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { getAuthToken, login as apiLogin, setAuthToken, verifySession } from '../api/client';
import { isSupabaseAuth, supabase } from '../lib/supabase';

interface AuthState {
  token: string | null;
  username: string | null;
  loading: boolean;
  login: (emailOrUsername: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  usesSupabase: boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getAuthToken());
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (isSupabaseAuth && supabase) {
        const { data } = await supabase.auth.getSession();
        const session = data.session;
        if (cancelled) return;
        if (session?.access_token) {
          setAuthToken(session.access_token);
          setToken(session.access_token);
          setUsername(session.user.email ?? session.user.id);
          try {
            const me = await verifySession();
            setUsername(me.username);
          } catch {
            setAuthToken(null);
            setToken(null);
            setUsername(null);
            await supabase.auth.signOut();
          }
        } else {
          setAuthToken(null);
          setToken(null);
          setUsername(null);
        }
        setLoading(false);
        return;
      }

      const t = getAuthToken();
      if (!t) {
        setLoading(false);
        return;
      }
      setToken(t);
      verifySession()
        .then((me) => {
          if (!cancelled) setUsername(me.username);
        })
        .catch(() => {
          if (!cancelled) {
            setAuthToken(null);
            setToken(null);
            setUsername(null);
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }

    bootstrap();

    if (isSupabaseAuth && supabase) {
      const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
        if (session?.access_token) {
          setAuthToken(session.access_token);
          setToken(session.access_token);
          setUsername(session.user.email ?? session.user.id);
        } else {
          setAuthToken(null);
          setToken(null);
          setUsername(null);
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
      const accessToken = data.session?.access_token;
      if (!accessToken) throw new Error('Sign in failed — no session returned');
      setAuthToken(accessToken);
      setToken(accessToken);
      setUsername(data.user?.email ?? data.user?.id ?? emailOrUsername.trim());
      return;
    }

    const res = await apiLogin(emailOrUsername, password);
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUsername(res.username);
  }, []);

  const logout = useCallback(async () => {
    if (isSupabaseAuth && supabase) {
      await supabase.auth.signOut();
    }
    setAuthToken(null);
    setToken(null);
    setUsername(null);
  }, []);

  const value = useMemo(
    () => ({
      token,
      username,
      loading,
      login,
      logout,
      isAuthenticated: Boolean(token),
      usesSupabase: isSupabaseAuth,
    }),
    [token, username, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
