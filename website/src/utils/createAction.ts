import type { CreateActionType } from '../context/CreateActionContext';

export type { CreateActionType };

export function getCreateActionForPath(pathname: string): CreateActionType | null {
  if (pathname.startsWith('/enquiries')) return 'enquiry';
  if (pathname.startsWith('/vendors')) return 'vendor';
  if (pathname.startsWith('/workers')) return 'worker';
  if (pathname.startsWith('/dishes')) return 'dish';
  if (pathname.startsWith('/invoices') || pathname.startsWith('/expenses')) return 'invoice';
  return null;
}

export function getSecondaryCreateActionForPath(pathname: string): CreateActionType | null {
  if (pathname.startsWith('/dishes')) return 'session';
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
      return 'New menu item';
    case 'invoice':
      return 'Upload bill';
    default:
      return 'Create';
  }
}

export function getSecondaryCreateButtonLabel(action: CreateActionType | null): string {
  if (action === 'session') return 'Add session';
  return 'Create';
}
