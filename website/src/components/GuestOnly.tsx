import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LoadingScreen } from './ui';

/** Only for /login — send signed-in users to the dashboard. */
export function GuestOnly() {
  const { loading, isAuthenticated } = useAuth();

  if (loading) return <LoadingScreen text="Checking sign-in…" />;
  if (isAuthenticated) return <Navigate to="/" replace />;

  return <Outlet />;
}
