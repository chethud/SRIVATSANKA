import type { Enquiry } from '../api/client';

export function isUnviewedEnquiry(enquiry: Enquiry): boolean {
  return enquiry.status === 'NEW' && !enquiry.ownerViewedAt;
}

export function isUnviewedOrder(enquiry: Enquiry): boolean {
  return enquiry.status === 'CONVERTED' && !enquiry.ownerViewedAt;
}

function byNewest(a: Enquiry, b: Enquiry): number {
  return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
}

export function sortEnquiriesForAttention(enquiries: Enquiry[]): Enquiry[] {
  return [...enquiries].sort((a, b) => {
    const aUnread = isUnviewedEnquiry(a) ? 0 : 1;
    const bUnread = isUnviewedEnquiry(b) ? 0 : 1;
    if (aUnread !== bUnread) return aUnread - bUnread;
    return byNewest(a, b);
  });
}

export function sortOrdersForAttention(orders: Enquiry[]): Enquiry[] {
  return [...orders].sort((a, b) => {
    const aUnread = isUnviewedOrder(a) ? 0 : 1;
    const bUnread = isUnviewedOrder(b) ? 0 : 1;
    if (aUnread !== bUnread) return aUnread - bUnread;
    return byNewest(a, b);
  });
}
