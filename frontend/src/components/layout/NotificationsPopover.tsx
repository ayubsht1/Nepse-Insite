import React, { useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { Bell, CheckCheck, AlertCircle, Newspaper, Zap, FileText } from 'lucide-react';

interface NotificationsPopoverProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotificationsPopover: React.FC<NotificationsPopoverProps> = ({ isOpen, onClose }) => {
  const { notifications, markNotificationAsRead, markAllNotificationsAsRead, unreadNotificationsCount } = useApp();
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getIcon = (type: string) => {
    switch (type) {
      case 'circuit':
        return <Zap className="w-4 h-4 text-amber-400" />;
      case 'news':
        return <Newspaper className="w-4 h-4 text-sky-400" />;
      case 'disclosure':
        return <FileText className="w-4 h-4 text-purple-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-emerald-400" />;
    }
  };

  return (
    <div
      ref={popoverRef}
      className="absolute -right-12 sm:right-0 top-full mt-2 w-[calc(100vw-2rem)] max-w-sm sm:w-96 bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xl z-50 overflow-hidden"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-[#151d30]">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-slate-500 dark:text-slate-300" />
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">Market Notifications</span>
          {unreadNotificationsCount > 0 && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-mono">
              ({unreadNotificationsCount} new)
            </span>
          )}
        </div>
        {unreadNotificationsCount > 0 && (
          <button
            onClick={markAllNotificationsAsRead}
            className="text-xs text-slate-500 hover:text-emerald-600 dark:text-slate-400 dark:hover:text-emerald-400 flex items-center gap-1 transition-colors"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            Mark all read
          </button>
        )}
      </div>

      <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800/60">
        {notifications.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500">
            No active notifications
          </div>
        ) : (
          notifications.map((item) => (
            <div
              key={item.id}
              onClick={() => markNotificationAsRead(item.id)}
              className={`p-3 transition-colors cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40 ${
                !item.read ? 'bg-slate-50/70 dark:bg-slate-800/20' : ''
              }`}
            >
              <div className="flex items-start gap-2.5">
                <div className="p-1.5 rounded bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shrink-0 mt-0.5">
                  {getIcon(item.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className={`text-xs font-medium truncate ${!item.read ? 'text-slate-900 dark:text-slate-100 font-semibold' : 'text-slate-600 dark:text-slate-300'}`}>
                      {item.title}
                    </p>
                    <span className="text-[10px] text-slate-400 dark:text-slate-500 shrink-0 font-mono">
                      {item.timestamp}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 mt-0.5 leading-relaxed">
                    {item.excerpt}
                  </p>
                  {item.relatedSymbol && (
                    <div className="mt-1.5 flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400 font-mono font-medium">
                      <span>Symbol: {item.relatedSymbol}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="p-2 border-t border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-[#0e1422] text-center">
        <span className="text-[11px] text-slate-500 dark:text-slate-400">
          Real-time alerts for price limits & news releases
        </span>
      </div>
    </div>
  );
};
