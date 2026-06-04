import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { Dish } from '../api/client';

export function DishSearchSelect({
  dishes,
  value,
  onChange,
  onSelectDish,
}: {
  dishes: Dish[];
  value: string;
  onChange: (dishId: string) => void;
  onSelectDish?: (dish: Dish | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const selected = dishes.find((d) => d.id === value);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return dishes.slice(0, 12);
    return dishes.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.category.toLowerCase().includes(q),
    ).slice(0, 12);
  }, [dishes, query]);

  function pick(d: Dish) {
    onChange(d.id);
    onSelectDish?.(d);
    setQuery('');
    setOpen(false);
  }

  return (
    <div className="relative flex-1 min-w-[220px]">
      <label className="text-xs text-[var(--muted)] font-medium mb-1 block">Search dish</label>
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
        <input
          type="search"
          value={open ? query : selected ? `${selected.name} (${selected.category})` : query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            if (!e.target.value) {
              onChange('');
              onSelectDish?.(null);
            }
          }}
          onFocus={() => {
            setOpen(true);
            setQuery(selected ? selected.name : '');
          }}
          placeholder="Search menu..."
          className="w-full pl-9 pr-8 py-2.5 border border-[var(--border)] rounded-lg text-sm bg-white"
        />
        {selected && !open && (
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-[var(--muted)] hover:text-[var(--primary)]"
            onClick={() => {
              onChange('');
              onSelectDish?.(null);
              setQuery('');
            }}
          >
            Clear
          </button>
        )}
      </div>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} aria-hidden />
          <ul className="absolute z-20 mt-1 w-full max-h-48 overflow-y-auto bg-white border border-[var(--border)] rounded-lg shadow-lg text-sm">
            {filtered.length === 0 ? (
              <li className="px-3 py-2 text-[var(--muted)]">No dishes found</li>
            ) : (
              filtered.map((d) => (
                <li key={d.id}>
                  <button
                    type="button"
                    className="w-full text-left px-3 py-2 hover:bg-[var(--primary-light)]"
                    onClick={() => pick(d)}
                  >
                    <span className="font-medium">{d.name}</span>
                    <span className="text-[var(--muted)] ml-2">{d.category} · ₹{d.price}</span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </>
      )}
    </div>
  );
}
