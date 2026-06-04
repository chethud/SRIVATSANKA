import type { CreateActionType } from '../context/CreateActionContext';

export type { CreateActionType };

export function getCreateActionForPath(pathname: string): CreateActionType | null {
  if (pathname.startsWith('/enquiries')) return 'enquiry';
  if (pathname.startsWith('/vendors')) return 'vendor';
  if (pathname.startsWith('/workers')) return 'worker';
  if (pathname.startsWith('/dishes')) return 'dish';
  if (pathname.startsWith('/invoices')) return 'invoice';
  return null;
}

export function getCreateButtonLabel(pathname: string): string {
  const action = getCreateActionForPath(pathname);
  switch (action) {
    case 'enquiry':
      return 'New enquiry';
    case 'vendor':
      return 'New vendor';
    case 'worker':
      return 'New worker';
    case 'dish':
      return 'New dish';
    case 'invoice':
      return 'Upload invoice';
    default:
      return 'Create';
  }
}
