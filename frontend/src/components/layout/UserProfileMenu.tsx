import React, { useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { Settings, LogOut } from 'lucide-react';
import { toast } from 'sonner';

interface UserProfileMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

export const UserProfileMenu: React.FC<UserProfileMenuProps> = ({ isOpen, onClose }) => {
  const { userProfile, userRole, setActiveTab, handleLogout } = useApp();
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
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

  const handleLogoutClick = async () => {
    try {
      await handleLogout();
      toast.info('Logged out');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to log out.');
    } finally {
      onClose();
    }
  };

  return (
    <div
      ref={menuRef}
      className="absolute right-0 top-full mt-2 w-[calc(100vw-2rem)] max-w-[280px] sm:w-72 bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xl z-50 overflow-hidden"
    >
      <div className="p-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#151d30]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-slate-200 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 flex items-center justify-center font-semibold text-emerald-600 dark:text-emerald-400 text-sm">
            {userProfile?.name
              .split(' ')
              .map((n) => n[0])
              .join('')}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">{userProfile?.name}</p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{userProfile?.email}</p>
            <div className="mt-1 flex items-center gap-1.5 text-[10px] text-slate-500 dark:text-slate-400">
              <span className="font-mono text-emerald-600 dark:text-emerald-400 uppercase font-semibold">
                {userRole}
              </span>
              <span>·</span>
              <span className="truncate">{userProfile?.brokerAffiliation || 'No affiliation'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-1">
        <button
          onClick={() => {
            setActiveTab('settings');
            onClose();
          }}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/50 rounded transition-colors"
        >
          <Settings className="w-4 h-4 text-slate-400" />
          <span>Account Settings</span>
        </button>

        <button
          onClick={handleLogoutClick}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/20 rounded transition-colors"
        >
          <LogOut className="w-4 h-4 text-rose-600 dark:text-rose-400" />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
};
