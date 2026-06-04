import { motion } from 'framer-motion';
import { TrendingDown, TrendingUp, type LucideIcon } from 'lucide-react';

type DashboardKpiCardProps = {
  label: string;
  value: string;
  subtext: string;
  icon: LucideIcon;
  trend?: { pct: number; up: boolean };
  gradient?: 1 | 2;
};

export function DashboardKpiCard({
  label,
  value,
  subtext,
  icon: Icon,
  trend,
  gradient = 1,
}: DashboardKpiCardProps) {
  const bg = gradient === 2 ? 'var(--kpi-gradient-2)' : 'var(--kpi-gradient-1)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="rounded-[var(--radius-xl)] p-5 border border-[var(--border)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow"
      style={{ background: bg }}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[11px] font-semibold tracking-wider text-[var(--muted)] uppercase">{label}</p>
        <div className="w-10 h-10 rounded-2xl bg-[var(--primary-light)] flex items-center justify-center shrink-0">
          <Icon size={20} className="text-[var(--primary)]" strokeWidth={2.25} />
        </div>
      </div>
      <p className="text-3xl font-bold text-[var(--foreground)] mt-3 tracking-tight">{value}</p>
      <div className="flex items-center justify-between mt-2 gap-2">
        <p className="text-sm text-[var(--muted)]">{subtext}</p>
        {trend && (
          <span
            className={`inline-flex items-center gap-0.5 text-xs font-semibold px-2 py-0.5 rounded-full ${
              trend.up ? 'bg-[var(--success-bg)] text-[var(--success-text)]' : 'bg-[var(--danger-bg)] text-[var(--danger)]'
            }`}
          >
            {trend.up ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {trend.pct}%
          </span>
        )}
      </div>
    </motion.div>
  );
}
