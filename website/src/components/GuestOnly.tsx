import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LoadingScreen } from './ui';

/** Guest routes (/login) — signed-in users go to the dashboard (or reset if recovering). */
export function GuestOnly() {
  const { loading, isAuthenticated, passwordRecovery } = useAuth();

  if (loading) return <LoadingScreen text="Checking sign-in…" />;
  if (passwordRecovery) return <Navigate to="/reset-password" replace />;
  if (isAuthenticated) return <Navigate to="/" replace />;

  return <Outlet />;
}
