import { useMemo, useState } from 'react';
import { Plus, Search } from 'lucide-react';
import type { Dish } from '../api/client';

export function DishSearchSelect({
  dishes,
  value,
  customName = '',
  onChange,
  onCustomNameChange,
  onSelectDish,
}: {
  dishes: Dish[];
  value: string;
  customName?: string;
  onChange: (dishId: string) => void;
  onCustomNameChange?: (name: string) => void;
  onSelectDish?: (dish: Dish | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const selected = dishes.find((d) => d.id === value);
  const trimmedQuery = query.trim();
  const hasCustom = Boolean(customName.trim()) && !value;

  const filtered = useMemo(() => {
    const q = trimmedQuery.toLowerCase();
    if (!q) return dishes.slice(0, 12);
    return dishes
      .filter(
        (d) =>
          d.name.toLowerCase().includes(q) ||
          d.category.toLowerCase().includes(q),
      )
      .slice(0, 12);
  }, [dishes, trimmedQuery]);

  function clearSelection() {
    onChange('');
    onCustomNameChange?.('');
    onSelectDish?.(null);
    setQuery('');
  }

  function pick(d: Dish) {
    onChange(d.id);
    onCustomNameChange?.('');
    onSelectDish?.(d);
    setQuery('');
    setOpen(false);
  }

  function pickCustom(name: string) {
    onChange('');
    onCustomNameChange?.(name);
    onSelectDish?.(null);
    setQuery('');
    setOpen(false);
  }

  const displayValue = open
    ? query
    : selected
      ? selected.name
      : hasCustom
        ? customName
        : query;

  return (
    <div className="relative flex-1 min-w-[220px]">
      <label className="text-xs text-[var(--muted)] font-medium mb-1 block">Search dish</label>
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
        <input
          type="search"
          value={displayValue}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            if (!e.target.value) {
              clearSelection();
            } else if (hasCustom || value) {
              onChange('');
              onCustomNameChange?.('');
              onSelectDish?.(null);
            }
          }}
          onFocus={() => {
            setOpen(true);
            setQuery(selected ? selected.name : hasCustom ? customName : query);
          }}
          placeholder="Search menu or type a new dish…"
          className="form-input w-full pl-9 pr-8 py-2.5 rounded-lg text-sm"
        />
        {(selected || hasCustom) && !open && (
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-[var(--muted)] hover:text-[var(--primary)]"
            onClick={clearSelection}
          >
            Clear
          </button>
        )}
      </div>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} aria-hidden />
          <ul className="absolute z-20 mt-1 w-full max-h-48 overflow-y-auto bg-[var(--card)] border border-[var(--border)] rounded-lg shadow-lg text-sm text-[var(--foreground)]">
            {filtered.length === 0 && !trimmedQuery ? (
              <li className="px-3 py-2 text-[var(--muted)]">Type to search the menu</li>
            ) : (
              filtered.map((d) => (
                <li key={d.id}>
                  <button
                    type="button"
                    className="w-full text-left px-3 py-2 text-[var(--foreground)] hover:bg-[var(--sidebar-hover)]"
                    onClick={() => pick(d)}
                  >
                    <span className="font-medium">{d.name}</span>
                    <span className="text-[var(--muted)] ml-2">{d.category}</span>
                  </button>
                </li>
              ))
            )}
            {trimmedQuery && filtered.every((d) => d.name.toLowerCase() !== trimmedQuery.toLowerCase()) && (
              <li className="border-t border-[var(--border)]">
                <button
                  type="button"
                  className="w-full text-left px-3 py-2.5 text-[var(--primary)] hover:bg-[var(--sidebar-hover)] flex items-center gap-2 font-medium"
                  onClick={() => pickCustom(trimmedQuery)}
                >
                  <Plus size={15} />
                  Add &quot;{trimmedQuery}&quot; to menu
                </button>
              </li>
            )}
          </ul>
        </>
      )}
      {hasCustom && (
        <p className="text-xs text-[var(--muted)] mt-1.5">
          New dish — will be saved to the menu catalog and added to this order.
        </p>
      )}
    </div>
  );
}
