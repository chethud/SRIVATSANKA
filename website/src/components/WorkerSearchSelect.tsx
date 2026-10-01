import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, Search } from 'lucide-react';
import type { Worker } from '../api/client';

export function WorkerSearchSelect({
  workers,
  onSelect,
  disabled = false,
  placeholder = 'Type to search workers…',
}: {
  workers: Worker[];
  onSelect: (worker: Worker) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlight, setHighlight] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = [...workers].sort((a, b) => a.name.localeCompare(b.name));
    if (!q) return list;
    return list.filter((w) => {
      const phone = w.phoneNumber ?? '';
      return (
        w.name.toLowerCase().includes(q) ||
        w.role.toLowerCase().includes(q) ||
        phone.includes(q)
      );
    });
  }, [workers, query]);

  useEffect(() => {
    setHighlight(0);
  }, [query, open, filtered.length]);

  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector('[data-highlight="true"]');
    el?.scrollIntoView({ block: 'nearest' });
  }, [highlight, open]);

  function pick(worker: Worker) {
    onSelect(worker);
    setQuery('');
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative z-0 w-full max-w-lg" data-worker-search-open={open ? 'true' : undefined}>
      <label className="text-xs font-semibold text-[var(--order-accent)] uppercase tracking-wide flex items-center gap-1 mb-2">
        <Search size={14} /> Assign worker
      </label>
      <div className="relative">
        <Search
          size={16}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none z-10"
        />
        <input
          type="search"
          role="combobox"
          aria-expanded={open}
          aria-controls="worker-search-listbox"
          aria-autocomplete="list"
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
              return;
            }
            if (!open && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
              setOpen(true);
              return;
            }
            if (!open || filtered.length === 0) return;
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              setHighlight((i) => (i + 1) % filtered.length);
            } else if (e.key === 'ArrowUp') {
              e.preventDefault();
              setHighlight((i) => (i - 1 + filtered.length) % filtered.length);
            } else if (e.key === 'Enter') {
              e.preventDefault();
              const w = filtered[highlight] ?? filtered[0];
              if (w) pick(w);
            }
          }}
          placeholder={placeholder}
          className="form-input w-full pl-9 pr-10 py-2.5 rounded-lg text-sm border-[var(--border-strong)]"
          autoComplete="off"
        />
        <ChevronDown
          size={18}
          className={`absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </div>

      {open && !disabled && (
        <div
          className="absolute z-50 mt-1 w-full rounded-lg border border-[var(--border-strong)] bg-[var(--card)] shadow-[var(--shadow-md)] overflow-hidden"
        >
          <p className="px-3 py-2 text-[0.6875rem] font-semibold uppercase tracking-wide text-[var(--muted)] border-b border-[var(--border)] bg-[var(--background-alt)]">
            {filtered.length === 0
              ? 'No matches'
              : `${filtered.length} worker${filtered.length === 1 ? '' : 's'} — ↑↓ to move, Enter to assign`}
          </p>
          <ul
            id="worker-search-listbox"
            ref={listRef}
            className="max-h-56 overflow-y-auto overscroll-contain text-sm text-[var(--foreground)]"
            role="listbox"
          >
            {filtered.length === 0 ? (
              <li className="px-3 py-3 text-[var(--muted)]">Try another name or role</li>
            ) : (
              filtered.map((w, index) => (
                <li key={w.id} role="option" aria-selected={index === highlight}>
                  <button
                    type="button"
                    data-highlight={index === highlight ? 'true' : undefined}
                    className={`w-full text-left px-3 py-2.5 border-b border-[var(--border)] last:border-0 transition-colors ${
                      index === highlight ? 'bg-[var(--primary-light)]' : 'hover:bg-[var(--sidebar-hover)]'
                    }`}
                    onMouseEnter={() => setHighlight(index)}
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
        </div>
      )}

      <p className="text-xs text-[var(--muted)] mt-2">
        Search by name, role, or phone. Use keyboard arrows to pick a row.
      </p>
    </div>
  );
}
