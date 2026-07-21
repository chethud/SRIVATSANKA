/** Short label for the top bar when the page has no search field. */
export function getTopNavTitle(pathname: string): string | null {
  const path = pathname.replace(/\/+$/, '') || '/';

  if (path === '/') return 'Dashboard';
  if (path === '/analytics') return 'Analytics';
  if (path === '/enquiries') return 'Enquiries';
  if (path === '/orders') return 'Orders';
  if (path.startsWith('/orders/')) return 'Order';
  if (path === '/dishes') return 'Menu';
  if (path === '/vendors') return 'Vendors';
  if (path === '/workers') return 'Workers';
  if (path.startsWith('/workers/')) return 'Worker profile';
  if (path === '/invoices') return 'Invoices';
  if (path === '/settings') return 'Settings';
  if (path === '/bot-tester' || path.startsWith('/bot-tester/')) return 'WhatsApp Chats';
  return null;
}
