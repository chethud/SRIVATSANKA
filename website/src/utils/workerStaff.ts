/** Workers that use a headcount field on dispatch instead of “one person = one assign”. */
export const STAFF_HEADCOUNT_WORKER_NAMES = ['Extra cleaners', 'Extra servers'] as const;

export function workerNeedsHeadcount(workerName: string): boolean {
  const n = workerName.trim().toLowerCase();
  return STAFF_HEADCOUNT_WORKER_NAMES.some((label) => label.toLowerCase() === n);
}
