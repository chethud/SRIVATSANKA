import type { Analytics, Dish, Enquiry, Notification, Vendor, Worker } from '../api/client';
import { orderAmountPaid, orderBillingTotal, orderDiscount } from './orderBilling';

export function calcTrend(current: number, previous: number): { pct: number; up: boolean } {
  if (previous === 0) return { pct: current > 0 ? 100 : 0, up: current >= 0 };
  const pct = Math.round(((current - previous) / previous) * 100);
  return { pct: Math.abs(pct), up: pct >= 0 };
}

export function getConvertedOrders(enquiries: Enquiry[]) {
  return enquiries.filter((e) => e.status === 'CONVERTED');
}

export function getRecentOrders(enquiries: Enquiry[], limit = 6) {
  return [...getConvertedOrders(enquiries)]
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, limit);
}

export function getUpcomingEvents(enquiries: Enquiry[], limit = 5) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return enquiries
    .filter((e) => e.status === 'CONVERTED' && new Date(e.eventDate) >= today)
    .sort((a, b) => new Date(a.eventDate).getTime() - new Date(b.eventDate).getTime())
    .slice(0, limit);
}

export function getTodaysEvents(enquiries: Enquiry[]) {
  const today = new Date().toDateString();
  return enquiries.filter(
    (e) => e.status === 'CONVERTED' && new Date(e.eventDate).toDateString() === today,
  );
}

export function getTopDishes(enquiries: Enquiry[], limit = 5) {
  const counts = new Map<string, number>();
  for (const e of enquiries) {
    for (const d of e.dishes ?? []) {
      counts.set(d.dishName, (counts.get(d.dishName) ?? 0) + (d.quantity || 1));
    }
  }
  return [...counts.entries()]
    .map(([name, qty]) => ({ name, qty }))
    .sort((a, b) => b.qty - a.qty)
    .slice(0, limit);
}

export type ChartPeriod = 'weekly' | 'monthly' | 'yearly';

export function buildChartSeries(analytics: Analytics | null, mode: ChartPeriod) {
  if (!analytics?.monthly?.length) return [];

  if (mode === 'monthly') {
    return analytics.monthly.map((m) => ({
      label: m.month.split(' ')[0] ?? m.month,
      revenue: m.revenue,
      expenses: m.expenses,
    }));
  }

  if (mode === 'yearly') {
    const byYear = new Map<string, { revenue: number; expenses: number }>();
    for (const m of analytics.monthly) {
      const parts = m.month.trim().split(/\s+/);
      const year = parts.length > 1 ? parts[parts.length - 1] : m.month;
      const cur = byYear.get(year) ?? { revenue: 0, expenses: 0 };
      cur.revenue += m.revenue;
      cur.expenses += m.expenses;
      byYear.set(year, cur);
    }
    return [...byYear.entries()].map(([label, v]) => ({
      label,
      revenue: v.revenue,
      expenses: v.expenses,
    }));
  }

  const last = analytics.monthly.slice(-4);
  return last.map((m, i) => ({
    label: `W${i + 1}`,
    revenue: Math.round(m.revenue / 4),
    expenses: Math.round(m.expenses / 4),
  }));
}

export function sparklineFromMonthly(analytics: Analytics | null, field: 'revenue' | 'expenses' | 'profit') {
  const rows = analytics?.monthly ?? [];
  if (!rows.length) return [0, 0, 0, 0, 0];
  return rows.slice(-8).map((m) => {
    if (field === 'revenue') return m.revenue;
    if (field === 'expenses') return m.expenses;
    return m.profit;
  });
}

export function buildForecast(analytics: Analytics | null) {
  const monthly = analytics?.monthly ?? [];
  if (monthly.length < 2) {
    return monthly.map((m) => ({ label: m.month.split(' ')[0] ?? m.month, actual: m.revenue, forecast: m.revenue }));
  }
  const last = monthly[monthly.length - 1];
  const prev = monthly[monthly.length - 2];
  const growth = last.revenue > 0 ? (last.revenue - prev.revenue) / (prev.revenue || 1) : 0;
  const nextVal = Math.max(0, last.revenue * (1 + growth * 0.5));
  return [
    ...monthly.slice(-5).map((m) => ({
      label: m.month.split(' ')[0] ?? m.month,
      actual: m.revenue,
      forecast: null as number | null,
    })),
    { label: 'Forecast', actual: null as number | null, forecast: nextVal },
  ];
}

export function getAiInsights(
  stats: { new_enquiries?: number } | null,
  analytics: Analytics | null,
  enquiries: Enquiry[],
): string[] {
  const insights: string[] = [];
  const profit = analytics?.net_profit ?? 0;
  const newEnq = stats?.new_enquiries ?? 0;
  const converted = enquiries.filter((e) => e.status === 'CONVERTED').length;

  if (newEnq > 0) insights.push(`${newEnq} new enquiry${newEnq > 1 ? 'ies' : ''} need follow-up — respond within 24h to improve conversion.`);
  if (profit < 0) insights.push('Expenses exceed revenue this period. Review uploaded bills on Invoices and order margins.');
  else if (profit > 0) insights.push(`Net profit is healthy at positive flow. ${converted} converted order${converted !== 1 ? 's' : ''} in pipeline.`);
  if ((analytics?.monthly?.length ?? 0) >= 2) {
    const m = analytics!.monthly!;
    const last = m[m.length - 1];
    const prev = m[m.length - 2];
    if (last.expenses > prev.expenses * 1.2) insights.push('Monthly costs rose more than 20% — check vendor payments and ingredient bills.');
  }
  if (insights.length === 0) insights.push('Operations look stable. Add orders and upload invoices to unlock deeper AI insights.');
  return insights.slice(0, 3);
}

export function getVendorSummary(vendors: Vendor[]) {
  return vendors.slice(0, 5).map((v) => ({
    id: v.id,
    name: v.businessName || v.name,
    category: v.category,
    status: 'Active',
  }));
}

export function getWorkerOverview(workers: Worker[]) {
  const byRole = workers.reduce<Record<string, number>>((acc, w) => {
    acc[w.role] = (acc[w.role] ?? 0) + 1;
    return acc;
  }, {});
  return { total: workers.length, byRole, workers: workers.slice(0, 6) };
}

export function getUnreadNotifications(notifications: Notification[]) {
  return notifications.filter((n) => !n.read).slice(0, 5);
}

export function orderRevenueEstimate(enquiry: Enquiry) {
  const paid = orderAmountPaid(enquiry);
  if (paid > 0) return paid;
  if (enquiry.paymentReceived) {
    return Math.max(0, orderBillingTotal(enquiry) - orderDiscount(enquiry));
  }
  return 0;
}

export function dishCatalogSize(dishes: Dish[]) {
  return dishes.length;
}
