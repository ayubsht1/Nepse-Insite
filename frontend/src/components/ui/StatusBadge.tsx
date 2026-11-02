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
        return 'text-emerald-400 bg-emerald-950/40 border-emerald-800/60';
      case 'danger':
        return 'text-rose-400 bg-rose-950/40 border-rose-800/60';
      case 'warning':
        return 'text-amber-400 bg-amber-950/40 border-amber-800/60';
      case 'info':
        return 'text-sky-400 bg-sky-950/40 border-sky-800/60';
      case 'purple':
        return 'text-purple-400 bg-purple-950/40 border-purple-800/60';
      default:
        return 'text-slate-300 bg-slate-900 border-slate-800';
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
