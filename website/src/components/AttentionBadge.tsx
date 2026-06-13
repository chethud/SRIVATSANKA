export function AttentionBadge({ label = 'Not opened' }: { label?: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide bg-[var(--sidebar-badge-bg)] text-[var(--sidebar-badge-text)]">
      {label}
    </span>
  );
}
