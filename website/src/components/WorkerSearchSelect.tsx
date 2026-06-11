import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { Worker } from '../api/client';

export function WorkerSearchSelect({
  workers,
  onSelect,
  disabled = false,
  placeholder = 'Search by name, role, or phone…',
}: {
  workers: Worker[];
  onSelect: (worker: Worker) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = [...workers].sort((a, b) => a.name.localeCompare(b.name));
    if (!q) return list.slice(0, 15);
    return list
      .filter((w) => {
        const phone = w.phoneNumber ?? '';
        return (
          w.name.toLowerCase().includes(q) ||
          w.role.toLowerCase().includes(q) ||
          phone.includes(q)
        );
      })
      .slice(0, 15);
  }, [workers, query]);

  function pick(worker: Worker) {
    onSelect(worker);
    setQuery('');
    setOpen(false);
  }

  return (
    <div className="relative w-full max-w-lg">
      <label className="text-xs font-semibold text-[var(--order-accent)] uppercase tracking-wide flex items-center gap-1 mb-2">
        <Search size={14} /> Search & add worker
      </label>
      <div className="relative">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none"
        />
        <input
          type="search"
          value={query}
          disabled={disabled}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setOpen(false);
              e.currentTarget.blur();
            }
            if (e.key === 'Enter' && filtered.length === 1) {
              e.preventDefault();
              pick(filtered[0]);
            }
          }}
          placeholder={placeholder}
          className="form-input w-full pl-9 pr-3 py-2.5 rounded-lg text-sm"
          autoComplete="off"
        />
      </div>
      {open && !disabled && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} aria-hidden />
          <ul
            className="absolute z-20 mt-1 w-full max-h-56 overflow-y-auto bg-[var(--card)] border border-[var(--border-strong)] rounded-lg shadow-[var(--shadow-md)] text-sm text-[var(--foreground)]"
            role="listbox"
          >
            {filtered.length === 0 ? (
              <li className="px-3 py-3 text-[var(--muted)]">No workers match your search</li>
            ) : (
              filtered.map((w) => (
                <li key={w.id} role="option">
                  <button
                    type="button"
                    className="w-full text-left px-3 py-2.5 hover:bg-[var(--sidebar-hover)] border-b border-[var(--border)] last:border-0 transition-colors"
                    onClick={() => pick(w)}
                  >
                    <span className="font-semibold block text-[var(--foreground)]">{w.name}</span>
                    <span className="text-xs text-[var(--muted)]">
                      {w.role}
                      {w.phoneNumber ? ` · ${w.phoneNumber}` : ''}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </>
      )}
      {!open && (
        <p className="text-xs text-[var(--muted)] mt-2">
          Type a name, role, or phone number — click a result to assign.
        </p>
      )}
    </div>
  );
}
