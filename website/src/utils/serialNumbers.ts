import type { Enquiry } from '../api/client';

/** Newest item gets #1, next oldest #2, etc. */
export function buildSerialNumberMap(items: Enquiry[]): Map<string, number> {
  const sorted = [...items].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
  const map = new Map<string, number>();
  sorted.forEach((item, index) => map.set(item.id, index + 1));
  return map;
}
