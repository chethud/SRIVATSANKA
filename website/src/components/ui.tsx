import { Search } from 'lucide-react';

export function ErrorBanner({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-sm">
      {message}
    </div>
  );
}

export function LoadingScreen({ text = 'Loading...' }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-[var(--muted)]">
      <div className="w-10 h-10 border-4 border-[var(--primary-light)] border-t-[var(--accent)] rounded-full animate-spin mb-4" />
      <p>{text}</p>
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
