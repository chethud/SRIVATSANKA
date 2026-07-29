import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AppDataProvider } from '../context/AppDataContext';
import { LoadingScreen } from './ui';

export function RequireAuth() {
  const { loading, isAuthenticated, passwordRecovery } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingScreen text="Checking sign-in…" />;
  if (passwordRecovery) {
    return <Navigate to="/reset-password" replace />;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return (
    <AppDataProvider>
      <Outlet />
    </AppDataProvider>
  );
}
