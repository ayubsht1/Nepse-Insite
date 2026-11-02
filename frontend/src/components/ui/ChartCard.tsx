import React from 'react';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  timeframeOptions?: string[];
  selectedTimeframe?: string;
  onTimeframeChange?: (timeframe: string) => void;
  actions?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  subtitle,
  timeframeOptions,
  selectedTimeframe,
  onTimeframeChange,
  actions,
  children,
  footer,
  className = '',
}) => {
  return (
    <div className={`min-w-0 p-3 sm:p-4 md:p-5 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800/80 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
          {subtitle && <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          {timeframeOptions && onTimeframeChange && (
            <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-[#0e1422] rounded-lg border border-slate-200 dark:border-slate-800">
              {timeframeOptions.map((tf) => (
                <button
                  key={tf}
                  onClick={() => onTimeframeChange(tf)}
                  className={`px-2 py-1 text-[11px] font-mono font-medium rounded transition-colors ${
                    selectedTimeframe === tf
                      ? 'bg-white dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 font-semibold shadow-xs'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          )}
          {actions}
        </div>
      </div>

      {/* Chart Canvas Viewport */}
      <div className="w-full min-w-0 flex-1 min-h-[220px] sm:min-h-[240px]">
        {children}
      </div>

      {/* Optional Footer */}
      {footer && (
        <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-800/80 text-[11px] text-slate-500 dark:text-slate-400">
          {footer}
        </div>
      )}
    </div>
  );
};
