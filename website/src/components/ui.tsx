import { Search } from 'lucide-react';

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-sm">
      {message}
    </div>
  );
}

export function LoadingScreen({ text = 'Loading dashboard...' }: { text?: string }) {
  return (
    <div className="min-h-[60vh] max-w-[1440px] mx-auto space-y-6 animate-fade-in px-4 py-8">
      <div className="skeleton h-10 w-64" />
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 grid-cards-equal">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton h-36 rounded-[var(--radius-xl)]" />
        ))}
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 grid-cards-equal">
        <div className="skeleton h-96 xl:col-span-2 rounded-[var(--radius-xl)]" />
        <div className="skeleton h-48 rounded-[var(--radius-xl)]" />
      </div>
      <p className="text-center text-sm text-[var(--muted)]">{text}</p>
    </div>
  );
}

export function SearchInput({
  value,
  onChange,
  placeholder = 'Search...',
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="relative w-full max-w-md">
      <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="form-input w-full pl-10 pr-4 py-2.5 rounded-lg text-sm focus:border-[var(--primary)] outline-none"
      />
    </div>
  );
}

export function FilterChips({
  options,
  selected,
  onSelect,
}: {
  options: { id: string; label: string }[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onSelect(o.id)}
          className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
            selected === o.id
              ? 'bg-[var(--primary)] text-white shadow-sm'
              : 'bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] hover:border-[var(--primary)]/50'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function FilterToolbar({
  sections,
}: {
  sections: {
    label: string;
    options: { id: string; label: string }[];
    selected: string;
    onSelect: (id: string) => void;
  }[];
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-3 sm:p-4 shadow-[var(--shadow-sm)] lg:flex-row lg:items-center lg:gap-0 lg:divide-x lg:divide-[var(--border)]">
      {sections.map((section) => (
        <div
          key={section.label}
          className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center sm:gap-3 lg:flex-1 lg:px-4 first:lg:pl-0 last:lg:pr-0"
        >
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)] shrink-0 sm:w-[4.25rem]">
            {section.label}
          </span>
          <FilterChips
            options={section.options}
            selected={section.selected}
            onSelect={section.onSelect}
          />
        </div>
      ))}
    </div>
  );
}
