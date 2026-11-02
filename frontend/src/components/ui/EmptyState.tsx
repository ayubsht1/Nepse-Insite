import React from 'react';
import { Database, Search, ArrowRight } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ComponentType<{ className?: string }>;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon: Icon = Database,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`p-8 md:p-12 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 text-center flex flex-col items-center justify-center max-w-lg mx-auto shadow-xs ${className}`}
    >
      <div className="w-12 h-12 rounded-xl bg-slate-100 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 flex items-center justify-center text-slate-400 dark:text-slate-500 mb-3">
        <Icon className="w-6 h-6" />
      </div>

      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm leading-relaxed">
        {description}
      </p>

      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-3.5 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors inline-flex items-center gap-1.5"
        >
          <span>{actionLabel}</span>
          <ArrowRight className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
        </button>
      )}
    </div>
  );
};
