import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  variant?: 'spinner' | 'skeleton-cards' | 'skeleton-table';
  count?: number;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading live market data...',
  variant = 'spinner',
  count = 4,
  className = '',
}) => {
  if (variant === 'skeleton-cards') {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 ${className}`}>
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="p-4 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 animate-pulse space-y-3"
          >
            <div className="h-3 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-7 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-2.5 w-40 bg-slate-200 dark:bg-slate-800 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'skeleton-table') {
    return (
      <div className={`rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] p-4 space-y-3 animate-pulse ${className}`}>
        <div className="h-8 bg-slate-100 dark:bg-[#0e1422] rounded border border-slate-200 dark:border-slate-800/80 mb-2" />
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="h-10 bg-slate-100 dark:bg-slate-800/50 rounded" />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`p-10 flex flex-col items-center justify-center text-center space-y-2 text-slate-400 ${className}`}
    >
      <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
      <span className="text-xs font-mono">{message}</span>
    </div>
  );
};
