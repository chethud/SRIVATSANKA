import { QUANTITY_UNITS, normalizeQuantityUnit } from '../../utils/quantityUnits';

type QuantityUnitFieldsProps = {
  quantity: number;
  unit: string;
  onQuantityChange: (value: number) => void;
  onUnitChange: (value: string) => void;
  quantityClassName?: string;
  unitClassName?: string;
  quantityLabel?: string;
  unitLabel?: string;
  idPrefix?: string;
};

export function QuantityUnitFields({
  quantity,
  unit,
  onQuantityChange,
  onUnitChange,
  quantityClassName = 'form-input w-full mt-1 px-3 py-2 rounded-lg text-sm',
  unitClassName = 'form-select w-full mt-1 px-3 py-2 rounded-lg text-sm',
  quantityLabel = 'Quantity',
  unitLabel = 'Unit',
  idPrefix = 'qty',
}: QuantityUnitFieldsProps) {
  return (
    <>
      <div>
        <label className="text-xs text-[var(--muted)]">{quantityLabel}</label>
        <input
          type="number"
          min={0.01}
          step="any"
          value={quantity}
          onChange={(e) => onQuantityChange(Math.max(0.01, Number(e.target.value) || 0.01))}
          className={quantityClassName}
        />
      </div>
      <div>
        <label className="text-xs text-[var(--muted)]">{unitLabel}</label>
        <select
          id={`${idPrefix}-unit`}
          value={normalizeQuantityUnit(unit)}
          onChange={(e) => onUnitChange(e.target.value)}
          className={unitClassName}
        >
          {QUANTITY_UNITS.map((u) => (
            <option key={u.value} value={u.value}>
              {u.label}
            </option>
          ))}
        </select>
      </div>
    </>
  );
}
