import { TrendingDown, TrendingUp, type LucideIcon } from 'lucide-react';
import { AnimatedCounter } from './AnimatedCounter';

type DashboardKpiCardProps = {
  label: string;
  value: string;
  numericValue?: number;
  subtext: string;
  icon: LucideIcon;
  trend?: { pct: number; up: boolean };
  gradient?: 1 | 2;
  formatValue?: (n: number) => string;
  onClick?: () => void;
};

export function DashboardKpiCard({
  label,
  value,
  numericValue,
  subtext,
  icon: Icon,
  trend,
  gradient = 1,
  formatValue,
  onClick,
}: DashboardKpiCardProps) {
  const bg = gradient === 2 ? 'var(--kpi-gradient-2)' : 'var(--kpi-gradient-1)';
  const interactive = Boolean(onClick);

  return (
    <div
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={`relative overflow-hidden rounded-[var(--radius-xl)] p-5 border border-[var(--border)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow min-w-0 w-full h-full ${
        interactive ? 'cursor-pointer hover:border-[var(--primary)]/40 focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/30' : ''
      }`}
      style={{ background: bg }}
    >
      <div className="absolute top-0 left-0 right-0 h-0.5 opacity-80" style={{ background: 'var(--kpi-accent-bar)' }} />

      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold tracking-wider text-[var(--muted)] uppercase">{label}</p>
          <p className="text-2xl font-bold text-[var(--foreground)] mt-2 tracking-tight tabular-nums">
            {numericValue != null && formatValue ? (
              <AnimatedCounter value={numericValue} format={formatValue} />
            ) : (
              value
            )}
          </p>
        </div>
        <div className="w-10 h-10 rounded-xl bg-[var(--primary-light)] border border-[var(--border)] flex items-center justify-center shrink-0">
          <Icon size={20} className="text-[var(--primary)]" strokeWidth={2.25} />
        </div>
      </div>

      <div className="flex items-center justify-between mt-2 gap-2">
        <p className="text-xs text-[var(--muted)]">{subtext}</p>
        {trend && (
          <span
            className={`inline-flex items-center gap-0.5 text-[11px] font-semibold px-2 py-0.5 rounded-md ${
              trend.up ? 'bg-[var(--success-bg)] text-[var(--success-text)]' : 'bg-[var(--danger-bg)] text-[var(--danger)]'
            }`}
          >
            {trend.up ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {trend.pct}%
          </span>
        )}
      </div>
    </div>
  );
}
