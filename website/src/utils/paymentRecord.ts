export type PaymentMode = 'cash' | 'online';

export const PAYMENT_MODE_OPTIONS: { id: PaymentMode; label: string }[] = [
  { id: 'cash', label: 'Cash' },
  { id: 'online', label: 'Online' },
];

export const RECEIVED_ACCOUNT_SUGGESTIONS = [
  'Cash in hand',
  'HDFC Current',
  'ICICI Current',
  'SBI Current',
  'PhonePe / UPI',
  'GPay / UPI',
];

export function defaultPaymentPaidAtLocal(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function paymentModeLabel(mode: string | null | undefined): string {
  if (mode === 'cash') return 'Cash';
  if (mode === 'online') return 'Online';
  return mode?.trim() || '—';
}
