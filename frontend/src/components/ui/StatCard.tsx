import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { formatPercent } from '../../lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  subtext?: string | React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  iconColor?: string;
  valueColor?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  changeLabel,
  subtext,
  icon: Icon,
  iconColor = 'text-slate-400',
  valueColor = 'text-white',
  trend,
}) => {
  const isPositive = change !== undefined ? change > 0 : trend === 'up';
  const isNegative = change !== undefined ? change < 0 : trend === 'down';

  return (
    <div className="p-4 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700/80 transition-colors shadow-xs">
      <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs mb-2">
        <span className="font-medium truncate">{title}</span>
        {Icon && <Icon className={`w-4 h-4 shrink-0 ${iconColor}`} />}
      </div>

      <div className="flex items-baseline gap-2 flex-wrap">
        <span className={`text-2xl font-bold font-mono tabular-nums tracking-tight text-slate-900 dark:text-white ${valueColor !== 'text-white' ? valueColor : ''}`}>
          {value}
        </span>

        {change !== undefined && (
          <span
            className={`text-xs font-mono tabular-nums font-semibold flex items-center gap-0.5 ${
              isPositive ? 'text-emerald-600 dark:text-emerald-400' : isNegative ? 'text-rose-600 dark:text-rose-400' : 'text-slate-500 dark:text-slate-400'
            }`}
          >
            {isPositive && <TrendingUp className="w-3.5 h-3.5 inline" />}
            {isNegative && <TrendingDown className="w-3.5 h-3.5 inline" />}
            <span>{formatPercent(change)}</span>
            {changeLabel && <span className="text-[10px] text-slate-400 dark:text-slate-500 ml-0.5 font-normal">{changeLabel}</span>}
          </span>
        )}
      </div>

      {subtext && (
        <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
          {typeof subtext === 'string' ? <span>{subtext}</span> : subtext}
        </div>
      )}
    </div>
  );
};
