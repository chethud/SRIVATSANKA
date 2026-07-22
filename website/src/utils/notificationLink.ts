import type { Enquiry, Notification } from '../api/client';

function customerNameFromMessage(notification: Notification): string | null {
  if (notification.type === 'CALLBACK_REMINDER') {
    const match = notification.message.match(/^Call\s+(.+?)\s+in\s+/i);
    return match?.[1]?.trim() ?? null;
  }
  const dash = notification.message.split(' – ');
  return dash[0]?.trim() || null;
}

function resolveEnquiryId(notification: Notification, enquiries: Enquiry[]): string | null {
  if (notification.enquiryId) return notification.enquiryId;
  const name = customerNameFromMessage(notification);
  if (!name) return null;
  const match = enquiries.find((e) => e.customerName === name);
  return match?.id ?? null;
}

/** Route for a dashboard notification click. */
export function getNotificationHref(notification: Notification, enquiries: Enquiry[]): string {
  const enquiryId = resolveEnquiryId(notification, enquiries);
  if (enquiryId) return `/enquiries?id=${encodeURIComponent(enquiryId)}`;
  if (notification.type === 'NEW_ENQUIRY' || notification.type === 'CALLBACK_REMINDER') {
    return '/enquiries';
  }
  return '/';
}
