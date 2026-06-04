import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import { TrendingDown, TrendingUp, type LucideIcon } from 'lucide-react';
import { AnimatedCounter } from './AnimatedCounter';

type DashboardKpiCardProps = {
  label: string;
  value: string;
  numericValue?: number;
  subtext: string;
  icon: LucideIcon;
  trend?: { pct: number; up: boolean };
  sparkline?: number[];
  gradient?: 1 | 2;
  formatValue?: (n: number) => string;
  sparkId?: string;
};

export function DashboardKpiCard({
  label,
  value,
  numericValue,
  subtext,
  icon: Icon,
  trend,
  sparkline = [],
  gradient = 1,
  formatValue,
  sparkId = 'kpi',
}: DashboardKpiCardProps) {
  const bg = gradient === 2 ? 'var(--kpi-gradient-2)' : 'var(--kpi-gradient-1)';
  const sparkData = useMemo(
    () => sparkline.map((v, i) => ({ i, v })),
    [sparkline],
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3, transition: { duration: 0.18 } }}
      className="relative overflow-hidden rounded-[var(--radius-xl)] p-5 border border-[var(--border)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow"
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

      {sparkData.length > 1 && (
        <div className="h-10 mt-3 -mx-1 opacity-70">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData}>
              <defs>
                <linearGradient id={`spark-${sparkId}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke="var(--primary)" strokeWidth={1.5} fill={`url(#spark-${sparkId})`} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

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
    </motion.div>
  );
}
