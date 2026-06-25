import { isSupabaseAuth, supabase } from '../lib/supabase';

/** Fallback when not using Vercel /api proxy (set VITE_API_URL instead). */
const DEFAULT_LIVE_API = 'https://srivatsanka.onrender.com';

function resolveApiBase(): string {
  const fromEnv = (import.meta.env.VITE_API_URL as string | undefined)?.trim().replace(/\/$/, '');
  if (fromEnv) return fromEnv;
  // Vercel production: vercel.json proxies /api → Render (same-origin, no CORS).
  if (import.meta.env.PROD) return '';
  return '';
}

const API_BASE = resolveApiBase();

export function getApiBaseUrl(): string {
  return API_BASE || (typeof window !== 'undefined' ? window.location.origin : DEFAULT_LIVE_API);
}

const AUTH_STORAGE_KEY = 'kannans_auth_token';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(AUTH_STORAGE_KEY, token);
    else localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

async function getBearerToken(): Promise<string | null> {
  if (isSupabaseAuth && supabase) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token ?? null;
    if (token) setAuthToken(token);
    return token;
  }
  return getAuthToken();
}

async function refreshBearerToken(): Promise<string | null> {
  if (isSupabaseAuth && supabase) {
    const { data, error } = await supabase.auth.refreshSession();
    if (error || !data.session?.access_token) return null;
    const token = data.session.access_token;
    setAuthToken(token);
    return token;
  }
  return getAuthToken();
}

async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const token = await getBearerToken();
  const h: Record<string, string> = {};
  if (token) h.Authorization = `Bearer ${token}`;
  if (extra instanceof Headers) {
    extra.forEach((v, k) => {
      h[k] = v;
    });
  } else if (Array.isArray(extra)) {
    for (const [k, v] of extra) h[k] = v;
  } else if (extra && typeof extra === 'object') {
    Object.assign(h, extra as Record<string, string>);
  }
  return h;
}

async function clearLegacySession(path: string): Promise<void> {
  setAuthToken(null);
  if (path !== '/api/auth/me' && typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
    window.location.assign('/login');
  }
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export interface AuthMe {
  username: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error(await apiErrorMessage(res, '/api/auth/login'));
  return res.json();
}

export async function verifySession(): Promise<AuthMe> {
  return apiFetch<AuthMe>('/api/auth/me');
}

export interface DashboardStats {
  new_enquiries: number;
  new_orders: number;
  total_enquiries: number;
  unread_notifications: number;
  total_dishes: number;
  upcoming_events: number;
  total_vendors: number;
  total_workers: number;
  total_expenses: number;
}

export interface EnquiryDish {
  id: string;
  dishId?: string | null;
  dishName: string;
  category: string;
  customizations: string | null;
  notes: string | null;
  quantity: number;
  quantityUnit?: string | null;
  unitPrice: number | null;
  served: boolean;
}

export interface Enquiry {
  id: string;
  customerName: string;
  phoneNumber: string;
  eventType: string;
  eventDate: string;
  eventLocation: string;
  guestCount: number;
  preferredCallbackAt: string;
  status: string;
  ownerViewedAt?: string | null;
  notes?: string | null;
  createdAt: string;
  dishes: EnquiryDish[];
}

export interface Dish {
  id: string;
  name: string;
  category: string;
  price: number;
  description: string | null;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
}

export interface Vendor {
  id: string;
  name: string;
  businessName: string | null;
  phoneNumber: string;
  category: string;
  notes: string | null;
  createdAt: string;
}

export interface Worker {
  id: string;
  name: string;
  phoneNumber: string;
  role: string;
  dailyWage: number;
  isLead?: boolean;
  createdAt: string;
}

export interface Expense {
  id: string;
  category: string;
  amount: number;
  description: string | null;
  expenseDate: string;
  createdAt: string;
}

export interface ChartMoneyItem {
  label: string;
  amount: number;
  date?: string | null;
  purpose?: string | null;
}

export interface MonthlyChartPoint {
  month: string;
  revenue: number;
  expenses: number;
  profit: number;
}

export interface Analytics {
  total_revenue: number;
  order_revenue: number;
  uploaded_revenue: number;
  total_expenses: number;
  global_expenses: number;
  order_expenses: number;
  net_profit: number;
  converted_orders: number;
  by_status?: Record<string, number>;
  by_event_type?: Record<string, number>;
  expense_items?: ChartMoneyItem[];
  profit_items?: ChartMoneyItem[];
  monthly?: MonthlyChartPoint[];
}

export interface InvoiceUpload {
  id: string;
  enquiryId: string;
  docType: string;
  fileName: string;
  amount: number | null;
  notes: string | null;
  createdAt: string;
}

export interface InvoiceUploadWithOrder extends InvoiceUpload {
  customerName: string;
  eventType: string;
  recognized?: boolean;
}

export interface WhatsAppStatus {
  configured: boolean;
  phone_number_id_set: boolean;
  token_set: boolean;
  owner_phone: string;
}

export interface BotTestResponse {
  reply: string;
  is_complete: boolean;
  enquiry_saved?: boolean;
  fields: Record<string, unknown>;
  media?: { url: string; caption?: string | null }[];
}

export interface ChatConversation {
  phoneNumber: string;
  customerName: string | null;
  lastMessage: string;
  lastRole: string;
  lastAt: string;
  messageCount: number;
  botPaused?: boolean;
}

export interface ChatMessage {
  id: string;
  phoneNumber: string;
  role: 'customer' | 'bot' | 'owner' | string;
  body: string;
  media?: { url: string; caption?: string | null }[];
  createdAt: string;
}

async function apiErrorMessage(res: Response, path: string): Promise<string> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d?.msg ?? String(d)).join(', ');
    }
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    if (body?.message) return String(body.message);
  } catch {
    /* ignore */
  }
  return `Request failed (${res.status}) at ${path}`;
}

async function parseApiResponse<T>(res: Response, path: string): Promise<T> {
  if (res.status === 401) {
    throw new Error(
      path === '/api/auth/me' ? 'Session expired' : 'Session expired. Please sign in again.',
    );
  }
  if (!res.ok) throw new Error(await apiErrorMessage(res, path));
  return res.json();
}

async function fetchWithAuth(path: string, options?: RequestInit, retried = false): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: await authHeaders(options?.headers),
  });
  if (res.status === 401 && !retried) {
    const refreshed = await refreshBearerToken();
    if (refreshed) return fetchWithAuth(path, options, true);
  }
  if (res.status === 401 && !isSupabaseAuth) {
    await clearLegacySession(path);
  }
  return res;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetchWithAuth(path, options);
  return parseApiResponse<T>(res, path);
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(20000) });
    return res.ok;
  } catch {
    return false;
  }
}

export const fetchStats = () => apiFetch<DashboardStats>('/api/stats');
export const fetchEnquiries = () => apiFetch<Enquiry[]>('/api/enquiries');
export const fetchDishes = () => apiFetch<Dish[]>('/api/dishes');
export const fetchNotifications = () => apiFetch<Notification[]>('/api/notifications');
export const fetchVendors = () => apiFetch<Vendor[]>('/api/vendors');
export const fetchWorkers = () => apiFetch<Worker[]>('/api/workers');
export const fetchExpenses = () => apiFetch<Expense[]>('/api/expenses');
export const fetchAnalytics = () => apiFetch<Analytics>('/api/analytics');
export const fetchWhatsAppStatus = () => apiFetch<WhatsAppStatus>('/api/whatsapp/status');

export async function createEnquiry(data: {
  customerName: string;
  phoneNumber: string;
  eventType: string;
  eventDate: string;
  eventLocation: string;
  guestCount?: number;
  preferredCallbackAt: string;
  notes?: string;
}): Promise<Enquiry> {
  return apiFetch<Enquiry>('/api/enquiries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateEnquiry(id: string, data: { notes?: string | null }): Promise<Enquiry> {
  return apiFetch<Enquiry>(`/api/enquiries/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateEnquiryStatus(id: string, status: string): Promise<Enquiry> {
  return apiFetch<Enquiry>(`/api/enquiries/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
}

export async function markEnquiryViewed(id: string): Promise<Enquiry> {
  return apiFetch<Enquiry>(`/api/enquiries/${id}/viewed`, { method: 'POST' });
}

export async function createDish(data: { name: string; category: string; price: number; description?: string }) {
  return apiFetch<Dish>('/api/dishes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function addOrderDish(
  enquiryId: string,
  data: {
    dishId?: string;
    dishName?: string;
    category?: string;
    quantity?: number;
    quantityUnit?: string;
    customizations?: string;
    notes?: string;
    unitPrice?: number;
  },
) {
  return apiFetch<Enquiry>(`/api/enquiries/${enquiryId}/dishes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateOrderDish(
  enquiryId: string,
  dishItemId: string,
  data: { category?: string; customizations?: string; notes?: string; quantity?: number; quantityUnit?: string; unitPrice?: number; served?: boolean },
) {
  return apiFetch<Enquiry>(`/api/enquiries/${enquiryId}/dishes/${dishItemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteOrderDish(enquiryId: string, dishItemId: string) {
  return apiFetch<Enquiry>(`/api/enquiries/${enquiryId}/dishes/${dishItemId}`, { method: 'DELETE' });
}

export interface InvoiceRecognizePreview {
  pendingId: string;
  fileName: string;
  description: string | null;
  expenseDate: string | null;
  amount: number | null;
  purpose: string | null;
  recognized: boolean;
  message?: string | null;
}

export interface InvoiceUploadResult extends InvoiceUpload {
  recognized: boolean;
}

export async function recognizeExpenseInvoice(file: File): Promise<InvoiceRecognizePreview> {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetchWithAuth('/api/invoices/recognize', {
    method: 'POST',
    body: fd,
  });
  return parseApiResponse<InvoiceRecognizePreview>(res, '/api/invoices/recognize');
}

export async function confirmExpenseInvoice(data: {
  pendingId: string;
  description?: string;
  expenseDate?: string;
  amount?: number;
  purpose?: string;
}) {
  return apiFetch<InvoiceUploadResult>('/api/invoices/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function cancelPendingInvoice(pendingId: string) {
  return apiFetch<{ ok: boolean }>(`/api/invoices/pending/${pendingId}`, { method: 'DELETE' });
}

export async function createVendor(data: Omit<Vendor, 'id' | 'createdAt'>) {
  return apiFetch<Vendor>('/api/vendors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteVendor(id: string) {
  return apiFetch<{ ok: boolean }>(`/api/vendors/${id}`, { method: 'DELETE' });
}

export async function createWorker(data: Omit<Worker, 'id' | 'createdAt'>) {
  return apiFetch<Worker>('/api/workers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function updateWorker(id: string, data: { isLead?: boolean }) {
  return apiFetch<Worker>(`/api/workers/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteWorker(id: string) {
  return apiFetch<{ ok: boolean }>(`/api/workers/${id}`, { method: 'DELETE' });
}

export interface WorkerAssignment {
  id: string;
  workerId: string;
  enquiryId: string | null;
  dutyDate: string;
  dutyType: string;
  wage: number;
  paymentCompleted: boolean;
  notes: string | null;
  createdAt: string;
  customerName: string | null;
  eventType: string | null;
  eventLocation: string | null;
  orderLabel: string | null;
}

export interface WorkerProfile {
  worker: Worker;
  assignments: WorkerAssignment[];
  totalDuties: number;
  upcomingDuties: number;
  totalWagesEarned: number;
}

export async function fetchWorkerProfile(workerId: string) {
  return apiFetch<WorkerProfile>(`/api/workers/${workerId}/profile`);
}

export async function createWorkerAssignment(
  workerId: string,
  data: { enquiryId?: string | null; dutyDate: string; dutyType: string; wage?: number; notes?: string },
) {
  return apiFetch<WorkerAssignment>(`/api/workers/${workerId}/assignments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function markWorkerAssignmentPaid(workerId: string, assignmentId: string) {
  return apiFetch<WorkerAssignment>(`/api/workers/${workerId}/assignments/${assignmentId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paymentCompleted: true }),
  });
}

export async function deleteWorkerAssignment(workerId: string, assignmentId: string) {
  return apiFetch<{ ok: boolean }>(`/api/workers/${workerId}/assignments/${assignmentId}`, {
    method: 'DELETE',
  });
}

export async function createExpense(data: { category: string; amount: number; description?: string }) {
  return apiFetch<Expense>('/api/expenses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function deleteExpense(id: string) {
  return apiFetch<{ ok: boolean }>(`/api/expenses/${id}`, { method: 'DELETE' });
}

export async function seedDemoData(): Promise<{
  enquiries: number;
  menuLines?: number;
  dishesInCatalog?: number;
  vendors: number;
  workers: number;
  workerAssignments?: number;
  expenses: number;
  marker: string;
}> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = import.meta.env.VITE_DEV_SEED_TOKEN;
  if (token) headers['X-Dev-Seed-Token'] = token;
  return apiFetch('/dev/seed', { method: 'POST', headers });
}

export async function testBotMessage(from: string, text: string): Promise<BotTestResponse> {
  return apiFetch<BotTestResponse>('/dev/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from_number: from, text }),
  });
}

export const fetchChatConversations = () => apiFetch<ChatConversation[]>('/api/chat/conversations');

export const fetchChatMessages = (phone: string) =>
  apiFetch<ChatMessage[]>(`/api/chat/conversations/${encodeURIComponent(phone)}/messages`);

export async function sendOwnerChatMessage(phone: string, text: string): Promise<{ ok: boolean; botPaused?: boolean }> {
  return apiFetch<{ ok: boolean; botPaused?: boolean }>(`/api/chat/conversations/${encodeURIComponent(phone)}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
}

export async function resumeChatBot(phone: string): Promise<{ ok: boolean; botPaused: boolean }> {
  return apiFetch<{ ok: boolean; botPaused: boolean }>(
    `/api/chat/conversations/${encodeURIComponent(phone)}/resume`,
    { method: 'POST' },
  );
}

export function normalizePhoneInput(value: string): string {
  return value.replace(/\D/g, '');
}

export function formatPhoneDisplay(digits: string): string {
  const d = normalizePhoneInput(digits);
  if (d.startsWith('91') && d.length === 12) {
    return `+91 ${d.slice(2, 7)} ${d.slice(7)}`;
  }
  if (d.length === 10) {
    return `+91 ${d.slice(0, 5)} ${d.slice(5)}`;
  }
  return d ? `+${d}` : '';
}

export async function askDashboardAssistant(query: string): Promise<{ reply: string }> {
  return apiFetch<{ reply: string }>('/api/ai-assistant', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true,
  });
}

export function formatCurrency(n: number) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(n);
}
