export const ENQUIRY_STATUS_LABELS: Record<string, string> = {
  NEW: 'New',
  SEEN: 'Seen',
  CONTACTED: 'Contacted',
  CONVERTED: 'Converted',
  NOT_CONVERTED: 'Not converted',
  CLOSED: 'Not converted',
};

export const ENQUIRY_STATUS_FILTERS = [
  { id: 'ALL', label: 'All' },
  { id: 'NEW', label: 'New' },
  { id: 'SEEN', label: 'Seen' },
  { id: 'CONTACTED', label: 'Contacted' },
  { id: 'CONVERTED', label: 'Converted' },
  { id: 'NOT_CONVERTED', label: 'Not converted' },
];

/** Status options in dropdown — never includes NEW unless it is the current value. */
export function statusOptionsForDropdown(current: string) {
  return Object.entries(ENQUIRY_STATUS_LABELS)
    .filter(([id]) => id !== 'CLOSED')
    .filter(([id]) => id === current || id !== 'NEW')
    .map(([id, label]) => ({ id, label }));
}

export function enquiryStatusLabel(status: string): string {
  return ENQUIRY_STATUS_LABELS[status] ?? status;
}
