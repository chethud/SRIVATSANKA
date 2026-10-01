import type { Vendor } from '../api/client';

export const DEFAULT_VENDOR_CATEGORIES = [
  'Marriage Halls',
  'Event Organizers',
  'Decorators',
  'Photographers',
  'DJs',
  'Vegetable Suppliers',
  'Rice Suppliers',
  'Transport Providers',
];

const STORAGE_KEY = 'srivatsanka_vendor_custom_categories';

export function readStoredVendorCategories(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];
    return data.map((x) => String(x).trim()).filter(Boolean);
  } catch {
    return [];
  }
}

export function storeVendorCategory(name: string): string[] {
  const label = name.trim();
  if (!label) return readStoredVendorCategories();
  const next = mergeVendorCategories(readStoredVendorCategories(), [label]);
  const customOnly = next.filter((c) => !DEFAULT_VENDOR_CATEGORIES.includes(c));
  localStorage.setItem(STORAGE_KEY, JSON.stringify(customOnly));
  return customOnly;
}

export function mergeVendorCategories(...groups: (string | undefined | null)[][]): string[] {
  const names = new Set<string>(DEFAULT_VENDOR_CATEGORIES);
  for (const group of groups) {
    for (const item of group) {
      const label = (item ?? '').trim();
      if (label) names.add(label);
    }
  }
  return Array.from(names).sort((a, b) => a.localeCompare(b));
}

export function categoriesFromVendors(vendors: Vendor[]): string[] {
  return vendors.map((v) => v.category).filter(Boolean);
}

export function pickCategoryValue(current: string, options: string[]): string {
  if (current && options.includes(current)) return current;
  return options[0] ?? '';
}
