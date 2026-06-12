import { createContext, useCallback, useContext, useEffect, useState, startTransition, type ReactNode } from 'react';
import {
  fetchStats,
  fetchEnquiries,
  fetchDishes,
  fetchNotifications,
  fetchVendors,
  fetchWorkers,
  fetchAnalytics,
  checkApiHealth,
  type DashboardStats,
  type Enquiry,
  type Dish,
  type Notification,
  type Vendor,
  type Worker,
  type Analytics,
} from '../api/client';

const POLL_MS = 8000;

interface AppData {
  connected: boolean;
  loading: boolean;
  lastSync: Date | null;
  error: string;
  stats: DashboardStats | null;
  enquiries: Enquiry[];
  dishes: Dish[];
  notifications: Notification[];
  vendors: Vendor[];
  workers: Worker[];
  analytics: Analytics | null;
  refresh: () => Promise<void>;
  refreshEnquiries: () => Promise<void>;
  patchEnquiry: (updated: Enquiry) => void;
}

const AppDataContext = createContext<AppData | null>(null);

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [error, setError] = useState('');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [enquiries, setEnquiries] = useState<Enquiry[]>([]);
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);

  const patchEnquiry = useCallback((updated: Enquiry) => {
    startTransition(() => {
      setEnquiries((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
    });
  }, []);

  const refreshEnquiries = useCallback(async () => {
    const e = await fetchEnquiries();
    startTransition(() => {
      setEnquiries(e);
    });
  }, []);

  const refresh = useCallback(async () => {
    try {
      const ok = await checkApiHealth();
      setConnected(ok);
      if (!ok) {
        setError('API offline. Check VITE_API_URL on Vercel or wait for Render to wake up.');
        return;
      }
      const [s, e, d, n, v, w, a] = await Promise.all([
        fetchStats(),
        fetchEnquiries(),
        fetchDishes(),
        fetchNotifications(),
        fetchVendors(),
        fetchWorkers(),
        fetchAnalytics(),
      ]);
      startTransition(() => {
        setStats(s);
        setEnquiries(e);
        setDishes(d);
        setNotifications(n);
        setVendors(v);
        setWorkers(w);
        setAnalytics(a);
        setError('');
        setLastSync(new Date());
      });
    } catch (err) {
      setConnected(false);
      const msg = err instanceof Error ? err.message : '';
      if (msg.includes('sign in') || msg.includes('Session expired')) {
        setError('Session expired. Please sign in again.');
      } else {
        setError(msg || 'Failed to load data from API.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = setInterval(() => {
      if (document.hidden) return;
      void refresh();
    }, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <AppDataContext.Provider
      value={{
        connected,
        loading,
        lastSync,
        error,
        stats,
        enquiries,
        dishes,
        notifications,
        vendors,
        workers,
        analytics,
        refresh,
        refreshEnquiries,
        patchEnquiry,
      }}
    >
      {children}
    </AppDataContext.Provider>
  );
}

export function useAppData() {
  const ctx = useContext(AppDataContext);
  if (!ctx) throw new Error('useAppData must be used within AppDataProvider');
  return ctx;
}
