import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, Plus, Search } from 'lucide-react';
import type { Dish } from '../api/client';

type ListOption =
  | { kind: 'dish'; dish: Dish }
  | { kind: 'custom'; name: string }
  | { kind: 'blocked' };

export function DishSearchSelect({
  dishes,
  value,
  customName = '',
  sessionCategory,
  blockedNames,
  onChange,
  onCustomNameChange,
  onSelectDish,
  onConfirmCustom,
  onConfirmDish,
}: {
  dishes: Dish[];
  value: string;
  customName?: string;
  /** Prefer dishes from this meal session (e.g. Lunch) in suggestions */
  sessionCategory?: string;
  /** Dish names already in this session (lowercase) — block re-adding */
  blockedNames?: string[];
  onChange: (dishId: string) => void;
  onCustomNameChange?: (name: string) => void;
  onSelectDish?: (dish: Dish | null) => void;
  /** Enter with typed custom name — parent can add immediately */
  onConfirmCustom?: (name: string) => void;
  /** Enter with exact catalog match — parent can add immediately */
  onConfirmDish?: (dish: Dish) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlight, setHighlight] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);

  const selected = dishes.find((d) => d.id === value);
  const trimmedQuery = query.trim();
  const hasCustom = Boolean(customName.trim()) && !value;
  const sessionKey = (sessionCategory ?? '').trim().toLowerCase();
  const blocked = useMemo(
    () => new Set((blockedNames ?? []).map((n) => n.trim().toLowerCase()).filter(Boolean)),
    [blockedNames],
  );
  const queryBlocked = Boolean(trimmedQuery) && blocked.has(trimmedQuery.toLowerCase());

  const filtered = useMemo(() => {
    const q = trimmedQuery.toLowerCase();
    const matchesQuery = (d: Dish) =>
      !q ||
      d.name.toLowerCase().includes(q) ||
      d.category.toLowerCase().includes(q);

    const inSession = (d: Dish) =>
      !sessionKey || d.category.trim().toLowerCase() === sessionKey;

    const sessionDishes = dishes.filter((d) => inSession(d) && matchesQuery(d));
    const otherDishes = sessionKey
      ? dishes.filter((d) => !inSession(d) && matchesQuery(d))
      : [];

    // Empty search: only this session's dishes (don't flood Lunch with Breakfast items).
    // With a query: session matches first, then other categories so you can still pick any dish.
    if (!q) {
      return sessionDishes.slice(0, 12);
    }
    return [...sessionDishes, ...otherDishes].slice(0, 12);
  }, [dishes, trimmedQuery, sessionKey]);

  const options = useMemo((): ListOption[] => {
    const rows: ListOption[] = filtered.map((dish) => ({ kind: 'dish', dish }));
    if (queryBlocked) {
      rows.push({ kind: 'blocked' });
    } else if (
      trimmedQuery &&
      filtered.every((d) => d.name.toLowerCase() !== trimmedQuery.toLowerCase())
    ) {
      rows.push({ kind: 'custom', name: trimmedQuery });
    }
    return rows;
  }, [filtered, queryBlocked, trimmedQuery]);

  const selectableCount = options.filter((o) => o.kind !== 'blocked').length;

  useEffect(() => {
    setHighlight(0);
  }, [query, open, options.length]);

  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector('[data-highlight="true"]');
    el?.scrollIntoView({ block: 'nearest' });
  }, [highlight, open]);

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

  function commitTypedName() {
    if (!trimmedQuery) return;
    if (blocked.has(trimmedQuery.toLowerCase())) return;
    const exact = filtered.find((d) => d.name.toLowerCase() === trimmedQuery.toLowerCase());
    if (exact) {
      pick(exact);
      onConfirmDish?.(exact);
      return;
    }
    pickCustom(trimmedQuery);
    onConfirmCustom?.(trimmedQuery);
  }

  function commitHighlighted() {
    const selectable = options.filter((o) => o.kind !== 'blocked');
    const opt = selectable[highlight] ?? selectable[0];
    if (!opt) {
      commitTypedName();
      return;
    }
    if (opt.kind === 'dish') {
      pick(opt.dish);
      onConfirmDish?.(opt.dish);
      return;
    }
    if (opt.kind === 'custom') {
      pickCustom(opt.name);
      onConfirmCustom?.(opt.name);
    }
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
      <label className="text-xs text-[var(--muted)] font-medium mb-1 block">Dish name</label>
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
        <input
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls="dish-search-listbox"
          aria-autocomplete="list"
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
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              setOpen(false);
              return;
            }
            if (!open && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
              e.preventDefault();
              setOpen(true);
              return;
            }
            if (e.key === 'ArrowDown') {
              e.preventDefault();
              if (!open) {
                setOpen(true);
                return;
              }
              if (selectableCount === 0) return;
              setHighlight((i) => (i + 1) % selectableCount);
              return;
            }
            if (e.key === 'ArrowUp') {
              e.preventDefault();
              if (!open || selectableCount === 0) return;
              setHighlight((i) => (i - 1 + selectableCount) % selectableCount);
              return;
            }
            if (e.key === 'Enter') {
              e.preventDefault();
              if (open && selectableCount > 0) {
                commitHighlighted();
              } else {
                commitTypedName();
              }
            }
          }}
          placeholder={
            sessionCategory
              ? `Search ${sessionCategory} menu or type any dish…`
              : 'Search menu or type any dish name…'
          }
          className={`form-input w-full pl-9 py-2.5 rounded-lg text-sm ${
            selected || hasCustom ? 'pr-20' : 'pr-10'
          }`}
          autoComplete="off"
        />
        <ChevronDown
          size={16}
          className={`absolute ${selected || hasCustom ? 'right-14' : 'right-3'} top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
        {(selected || hasCustom) && (
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-medium text-[var(--muted)] hover:text-[var(--primary)]"
            onClick={(e) => {
              e.preventDefault();
              clearSelection();
              setOpen(false);
            }}
          >
            Clear
          </button>
        )}
      </div>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} aria-hidden />
          <ul
            id="dish-search-listbox"
            ref={listRef}
            role="listbox"
            className="absolute z-20 mt-1 w-full max-h-52 overflow-y-auto bg-[var(--card)] border border-[var(--border)] rounded-lg shadow-lg text-sm text-[var(--foreground)]"
          >
            {options.length === 0 ? (
              <li className="px-3 py-2 text-[var(--muted)]">
                {sessionCategory
                  ? `No ${sessionCategory} dishes in catalog — type a name to add`
                  : 'Type a dish name'}
              </li>
            ) : (
              <>
                <li className="px-3 py-1.5 text-[0.6875rem] font-semibold uppercase tracking-wide text-[var(--muted)] border-b border-[var(--border)] bg-[var(--background-alt)] sticky top-0">
                  ↑↓ to move, Enter to add
                </li>
                {(() => {
                  let selectableIndex = -1;
                  return options.map((opt, index) => {
                    if (opt.kind === 'blocked') {
                      return (
                        <li
                          key={`blocked-${index}`}
                          className="px-3 py-2 text-[var(--muted)] border-t border-[var(--border)]"
                        >
                          Already added in this session
                        </li>
                      );
                    }
                    selectableIndex += 1;
                    const rowIndex = selectableIndex;
                    const isHighlight = rowIndex === highlight;
                    if (opt.kind === 'custom') {
                      return (
                        <li key={`custom-${opt.name}`} role="option" aria-selected={isHighlight}>
                          <button
                            type="button"
                            data-highlight={isHighlight ? 'true' : undefined}
                            className={`w-full text-left px-3 py-2.5 border-t border-[var(--border)] flex items-center gap-2 font-medium ${
                              isHighlight
                                ? 'bg-[var(--primary-light)] text-[var(--primary)]'
                                : 'text-[var(--primary)] hover:bg-[var(--sidebar-hover)]'
                            }`}
                            onMouseEnter={() => setHighlight(rowIndex)}
                            onClick={() => pickCustom(opt.name)}
                          >
                            <Plus size={15} />
                            Use &quot;{opt.name}&quot; on this order
                          </button>
                        </li>
                      );
                    }
                    const d = opt.dish;
                    const sameSession =
                      sessionKey && d.category.trim().toLowerCase() === sessionKey;
                    return (
                      <li key={d.id} role="option" aria-selected={isHighlight}>
                        <button
                          type="button"
                          data-highlight={isHighlight ? 'true' : undefined}
                          className={`w-full text-left px-3 py-2 text-[var(--foreground)] ${
                            isHighlight ? 'bg-[var(--primary-light)]' : 'hover:bg-[var(--sidebar-hover)]'
                          }`}
                          onMouseEnter={() => setHighlight(rowIndex)}
                          onClick={() => pick(d)}
                        >
                          <span className="font-medium">{d.name}</span>
                          {!sameSession && (
                            <span className="text-[var(--muted)] ml-2">{d.category}</span>
                          )}
                        </button>
                      </li>
                    );
                  });
                })()}
              </>
            )}
          </ul>
        </>
      )}
      {hasCustom && (
        <p className="text-xs text-[var(--muted)] mt-1.5">
          New dish — it will be added to this session and (by default) saved to the master Menu list. Duplicates are blocked.
        </p>
      )}
    </div>
  );
}
