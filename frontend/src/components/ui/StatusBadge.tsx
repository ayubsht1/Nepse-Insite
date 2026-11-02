import React from 'react';

export type StatusVariant =
  | 'success'
  | 'danger'
  | 'warning'
  | 'info'
  | 'neutral'
  | 'purple';

interface StatusBadgeProps {
  label: string;
  variant?: StatusVariant;
  icon?: React.ComponentType<{ className?: string }>;
  dot?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  variant = 'neutral',
  icon: Icon,
  dot = false,
  className = '',
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'success':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200 dark:text-emerald-400 dark:bg-emerald-950/40 dark:border-emerald-800/60';
      case 'danger':
        return 'text-rose-700 bg-rose-50 border-rose-200 dark:text-rose-400 dark:bg-rose-950/40 dark:border-rose-800/60';
      case 'warning':
        return 'text-amber-700 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-950/40 dark:border-amber-800/60';
      case 'info':
        return 'text-sky-700 bg-sky-50 border-sky-200 dark:text-sky-400 dark:bg-sky-950/40 dark:border-sky-800/60';
      case 'purple':
        return 'text-purple-700 bg-purple-50 border-purple-200 dark:text-purple-400 dark:bg-purple-950/40 dark:border-purple-800/60';
      default:
        return 'text-slate-700 bg-slate-100 border-slate-200 dark:text-slate-300 dark:bg-slate-900 dark:border-slate-800';
    }
  };

  const getDotStyles = () => {
    switch (variant) {
      case 'success':
        return 'bg-emerald-400';
      case 'danger':
        return 'bg-rose-400';
      case 'warning':
        return 'bg-amber-400';
      case 'info':
        return 'bg-sky-400';
      case 'purple':
        return 'bg-purple-400';
      default:
        return 'bg-slate-400';
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border font-mono tracking-wide ${getVariantStyles()} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${getDotStyles()}`} />}
      {Icon && <Icon className="w-3 h-3" />}
      <span>{label}</span>
    </span>
  );
};
