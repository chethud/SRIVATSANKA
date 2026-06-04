import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { getAuthToken, login as apiLogin, setAuthToken, verifySession } from '../api/client';

interface AuthState {
  token: string | null;
  username: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getAuthToken());
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(getAuthToken()));

  useEffect(() => {
    const t = getAuthToken();
    if (!t) {
      setLoading(false);
      return;
    }
    setToken(t);
    verifySession()
      .then((me) => {
        setUsername(me.username);
      })
      .catch(() => {
        setAuthToken(null);
        setToken(null);
        setUsername(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (user: string, password: string) => {
    const res = await apiLogin(user, password);
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUsername(res.username);
  }, []);

  const logout = useCallback(() => {
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
