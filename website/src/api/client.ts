const API_BASE = import.meta.env.VITE_API_URL || '';

export interface DashboardStats {
  new_enquiries: number;
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
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) throw new Error(`API error: ${path}`);
  return res.json();
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(3000) });
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
  guestCount: number;
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

export async function createDish(data: { name: string; category: string; price: number; description?: string }) {
  return apiFetch<Dish>('/api/dishes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export async function addOrderDish(
  enquiryId: string,
  data: { dishId: string; quantity?: number; customizations?: string; notes?: string; unitPrice?: number },
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
  data: { customizations?: string; notes?: string; quantity?: number; unitPrice?: number; served?: boolean },
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

export interface InvoiceUploadResult extends InvoiceUpload {
  recognized: boolean;
}

export async function uploadExpenseInvoice(file: File): Promise<InvoiceUploadResult> {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`${API_BASE}/api/invoices/upload`, { method: 'POST', body: fd });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
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
  vendors: number;
  workers: number;
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
