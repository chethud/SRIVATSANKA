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
  getApiBaseUrl,
  markEnquiryViewed as markEnquiryViewedApi,
  markNotificationsRead as markNotificationsReadApi,
  type DashboardStats,
  type Enquiry,
  type Dish,
  type Notification,
  type Vendor,
  type Worker,
  type Analytics,
} from '../api/client';

const POLL_MS = 8000;

function enquiryFingerprint(e: Enquiry): string {
  return [
    e.id,
    e.status,
    e.notes ?? '',
    e.ownerViewedAt ?? '',
    e.eventDate,
    e.guestCount ?? '',
    e.eventLocation ?? '',
    e.customerName,
    e.phoneNumber,
    ...(e.dishes ?? []).map((d) => `${d.id}:${d.served}:${d.dishName}:${d.category}:${d.customizations ?? ''}`),
  ].join('|');
}

function mergeEnquiries(prev: Enquiry[], next: Enquiry[]): Enquiry[] {
  if (prev.length === 0) return next;
  const prevById = new Map(prev.map((e) => [e.id, e]));
  let changed = prev.length !== next.length;
  const merged = next.map((incoming) => {
    const existing = prevById.get(incoming.id);
    if (existing && enquiryFingerprint(existing) === enquiryFingerprint(incoming)) {
      return existing;
    }
    changed = true;
    return incoming;
  });
  if (!changed) {
    for (const e of prev) {
      if (!next.some((n) => n.id === e.id)) {
        changed = true;
        break;
      }
    }
  }
  return changed ? merged : prev;
}

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
  refreshDishes: () => Promise<void>;
  patchEnquiry: (updated: Enquiry) => void;
  markEnquiryViewed: (id: string) => Promise<void>;
  markNotificationsRead: (ids?: string[]) => Promise<void>;
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

  const markNotificationsRead = useCallback(async (ids?: string[]) => {
    const unreadIds = ids ?? notifications.filter((n) => !n.read).map((n) => n.id);
    if (unreadIds.length === 0) return;
    const idSet = new Set(unreadIds);
    startTransition(() => {
      setNotifications((prev) =>
        prev.map((n) => (idSet.has(n.id) ? { ...n, read: true } : n)),
      );
      setStats((prev) => {
        if (!prev) return prev;
        const marked = notifications.filter((n) => idSet.has(n.id) && !n.read).length;
        return {
          ...prev,
          unread_notifications: Math.max(0, prev.unread_notifications - marked),
        };
      });
    });
    try {
      await markNotificationsReadApi(unreadIds);
    } catch {
      /* badge will refresh on next poll */
    }
  }, [notifications]);

  const markEnquiryViewed = useCallback(async (id: string) => {
    const current = enquiries.find((e) => e.id === id);
    if (!current || current.ownerViewedAt) return;
    try {
      const updated = await markEnquiryViewedApi(id);
      patchEnquiry(updated);
      startTransition(() => {
        setStats((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            new_enquiries: Math.max(0, prev.new_enquiries - 1),
            new_orders:
              updated.status === 'CONVERTED' ? Math.max(0, prev.new_orders - 1) : prev.new_orders,
          };
        });
      });
    } catch {
      /* ignore — badge will refresh on next poll */
    }
  }, [enquiries, patchEnquiry]);

  const refreshEnquiries = useCallback(async () => {
    const e = await fetchEnquiries();
    startTransition(() => {
      setEnquiries(e);
    });
  }, []);

  const refreshDishes = useCallback(async () => {
    const d = await fetchDishes();
    startTransition(() => {
      setDishes(d);
    });
  }, []);

  const refresh = useCallback(async () => {
    try {
      const ok = await checkApiHealth();
      setConnected(ok);
      if (!ok) {
        const base = getApiBaseUrl();
        setError(
          `API offline (${base}/api/health). On Vercel delete VITE_API_URL to use the built-in /api proxy, or set it to https://srivatsanka.onrender.com, then redeploy.`,
        );
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
        setEnquiries((prev) => mergeEnquiries(prev, e));
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
        setError(
          'API rejected your sign-in token. Set SUPABASE_URL and SUPABASE_ANON_KEY on the API (.env locally, or Render env), then restart/redeploy.',
        );
      } else if (msg.includes('rejected the token')) {
        setError(msg);
      } else if (msg === 'Failed to fetch') {
        const base = getApiBaseUrl();
        setError(
          `Cannot reach the API (${base}). On Vercel delete VITE_API_URL (uses /api proxy) or set it to https://srivatsanka.onrender.com, then redeploy.`,
        );
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
        refreshDishes,
        patchEnquiry,
        markEnquiryViewed,
        markNotificationsRead,
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
