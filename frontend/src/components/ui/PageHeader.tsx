import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  badge,
  actions,
  icon: Icon,
}) => {
  return (
    <div className="flex min-w-0 flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
      <div className="min-w-0 space-y-1">
        <div className="flex min-w-0 flex-wrap items-center gap-2.5">
          {Icon && (
            <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 shrink-0">
              <Icon className="w-4 h-4" />
            </div>
          )}
          <h1 className="min-w-0 text-lg sm:text-xl font-bold tracking-tight text-slate-900 dark:text-white font-display break-words">
            {title}
          </h1>
          {badge}
        </div>
        {description && (
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-3xl leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex w-full sm:w-auto flex-wrap items-center gap-2.5 sm:shrink-0 self-start sm:self-auto">
          {actions}
        </div>
      )}
    </div>
  );
};
