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
    <div className="max-w-[1440px] mx-auto space-y-6 animate-fade-in">
      <div className="skeleton h-10 w-64" />
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton h-36 rounded-[var(--radius-xl)]" />
        ))}
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="skeleton h-96 xl:col-span-2 rounded-[var(--radius-xl)]" />
        <div className="skeleton h-96 rounded-[var(--radius-xl)]" />
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
        className="w-full pl-10 pr-4 py-2.5 border border-[var(--border)] rounded-lg text-sm bg-white focus:border-[var(--primary)] outline-none"
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
    <div className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onSelect(o.id)}
          className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
            selected === o.id
              ? 'bg-[var(--primary)] text-white shadow-sm'
              : 'bg-[var(--card)] border border-[var(--border)] hover:border-[var(--accent)]'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
