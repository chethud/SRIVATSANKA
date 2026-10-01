export const EVENT_TYPES = [
  'Wedding',
  'House Warming',
  'Baby Shower',
  'Reception',
  'Corporate Lunch',
  'Naming Ceremony',
  'Other',
] as const;

export function defaultEventDateIso() {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().slice(0, 10);
}

export function defaultCallbackAtLocal() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(10, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export type CustomerEventFormState = {
  customerName: string;
  phoneNumber: string;
  eventType: string;
  eventDate: string;
  eventLocation: string;
  preferredCallbackAt: string;
  adminNote: string;
};

export function emptyCustomerEventForm(): CustomerEventFormState {
  return {
    customerName: '',
    phoneNumber: '',
    eventType: EVENT_TYPES[0],
    eventDate: defaultEventDateIso(),
    eventLocation: '',
    preferredCallbackAt: defaultCallbackAtLocal(),
    adminNote: '',
  };
}
