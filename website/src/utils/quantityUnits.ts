export const QUANTITY_UNITS = [
  { value: 'pcs', label: 'Pieces' },
  { value: 'kg', label: 'Kilogram (kg)' },
  { value: 'g', label: 'Gram (g)' },
  { value: 'L', label: 'Liter (L)' },
  { value: 'ml', label: 'Milliliter (ml)' },
  { value: 'box', label: 'Box' },
  { value: 'tray', label: 'Tray' },
  { value: 'dozen', label: 'Dozen' },
  { value: 'nos', label: 'Nos.' },
  { value: 'serving', label: 'Serving' },
  { value: 'cup', label: 'Cup' },
  { value: 'plate', label: 'Plate' },
  { value: 'bowl', label: 'Bowl' },
  { value: 'packet', label: 'Packet' },
  { value: 'bundle', label: 'Bundle' },
  { value: 'tin', label: 'Tin' },
] as const;

export type QuantityUnit = (typeof QUANTITY_UNITS)[number]['value'];

export function normalizeQuantityUnit(unit?: string | null): QuantityUnit {
  const u = (unit || 'pcs').trim();
  return (QUANTITY_UNITS.some((x) => x.value === u) ? u : 'pcs') as QuantityUnit;
}

export function formatQuantityDisplay(quantity: number, _unit?: string | null): string {
  return quantity % 1 === 0 ? String(quantity) : String(Math.round(quantity * 100) / 100);
}
