import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { getNepalDateTime } from '../../lib/utils';
import { NotificationsPopover } from './NotificationsPopover';
import { UserProfileMenu } from './UserProfileMenu';
import {
  Search,
  Bell,
  Menu,
  Activity,
  Calendar,
  Clock,
  Shield,
  Briefcase,
  Eye,
  ChevronDown,
  Sun,
  Moon,
} from 'lucide-react';

export const TopNavigation: React.FC = () => {
  const {
    userProfile,
    userRole,
    setIsSearchOpen,
    setMobileMenuOpen,
    unreadNotificationsCount,
    setActiveTab,
    theme,
    toggleTheme,
  } = useApp();

  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const nepalTime = getNepalDateTime();

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 px-2 py-0.5 rounded">
            <Shield className="w-3 h-3" />
            ADMIN
          </span>
        );
      case 'analyst':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-sky-700 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800/60 px-2 py-0.5 rounded">
            <Briefcase className="w-3 h-3" />
            ANALYST
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-2 py-0.5 rounded">
            <Eye className="w-3 h-3" />
            VIEWER
          </span>
        );
    }
  };

  return (
    <header className="h-16 shrink-0 min-w-0 bg-white dark:bg-[#0B0F19] border-b border-slate-200 dark:border-slate-800/90 px-2.5 sm:px-4 md:px-6 flex items-center justify-between gap-2 sm:gap-4 sticky top-0 z-40 transition-colors">
      {/* Left Zone: Mobile toggle + Brand Wordmark */}
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <button
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          className="md:hidden p-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60 rounded-lg transition-colors"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <button
          onClick={() => setActiveTab('overview')}
          className="flex items-center gap-2 sm:gap-2.5 cursor-pointer group"
          aria-label="Go to market overview"
        >
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500 dark:text-emerald-400 group-hover:bg-emerald-500/20 group-hover:border-emerald-500/40 transition-colors">
            <Activity className="w-5 h-5" />
          </div>
          <div className="max-[380px]:hidden">
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm sm:text-base tracking-tight text-slate-900 dark:text-white font-display">
                NEPSE <span className="text-emerald-500 dark:text-emerald-400">Insight</span>
              </span>
            </div>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 hidden sm:block tracking-wide">
              Market Intelligence Terminal
            </p>
          </div>
        </button>
      </div>

      {/* Center Zone: Global Search Bar */}
      <div className="flex-1 min-w-0 max-w-md mx-0 sm:mx-6">
        <button
          onClick={() => setIsSearchOpen(true)}
          className="w-full flex items-center justify-between px-2.5 sm:px-3.5 py-1.5 min-h-[38px] text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-[#111827] hover:bg-slate-200/80 dark:hover:bg-slate-800/80 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 rounded-lg shadow-inner transition-all group"
        >
          <div className="flex min-w-0 items-center gap-2 truncate">
            <Search className="w-4 h-4 shrink-0 text-slate-400 dark:text-slate-500 group-hover:text-emerald-500 dark:group-hover:text-emerald-400 transition-colors" />
            <span className="truncate hidden sm:inline">Search companies, symbols (e.g. NABIL)...</span>
            <span className="truncate sm:hidden text-[11px] max-[380px]:hidden">Search NEPSE...</span>
          </div>
          <div className="hidden sm:flex items-center gap-1 shrink-0">
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded">
              ⌘K
            </kbd>
          </div>
        </button>
      </div>

      {/* Right Zone: Market Date/Time + Notification + Role Badge + Profile */}
      <div className="flex items-center gap-1 sm:gap-3 shrink-0">
        {/* Market Status & Date */}
        <div className="hidden xl:flex items-center gap-3 px-3 py-1 bg-slate-100 dark:bg-[#111827] border border-slate-200 dark:border-slate-800/80 rounded-lg text-xs">
          <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-medium">{nepalTime.dateBs}</span>
          </div>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400 font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>{nepalTime.timeNPT} NPT</span>
          </div>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                nepalTime.isMarketOpen ? 'bg-emerald-500' : 'bg-slate-400'
              }`}
            />
            <span
              className={`text-[11px] font-semibold uppercase tracking-wider ${
                nepalTime.isMarketOpen ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'
              }`}
            >
              {nepalTime.isMarketOpen ? 'Market Open' : 'Market Closed'}
            </span>
          </div>
        </div>

        {/* Theme Toggle Button (Light/Dark Mode) */}
        <button
          onClick={toggleTheme}
          className="w-9 h-9 flex items-center justify-center text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60 rounded-lg transition-colors"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <Sun className="w-5 h-5 text-amber-400" />
          ) : (
            <Moon className="w-5 h-5 text-sky-500" />
          )}
        </button>

        {/* Notifications Icon with popover */}
        <div className="relative">
          <button
            onClick={() => {
              setIsNotifOpen((prev) => !prev);
              setIsProfileOpen(false);
            }}
            className="relative w-9 h-9 flex items-center justify-center text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60 rounded-lg transition-colors"
            aria-label="View notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-emerald-500 rounded-full" />
            )}
          </button>
          <NotificationsPopover isOpen={isNotifOpen} onClose={() => setIsNotifOpen(false)} />
        </div>

        {/* User Profile & Role dropdown */}
        <div className="relative">
          <button
            onClick={() => {
              setIsProfileOpen((prev) => !prev);
              setIsNotifOpen(false);
            }}
            className="flex items-center gap-2.5 p-1 sm:px-2.5 sm:py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/60 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 flex items-center justify-center font-bold text-xs text-emerald-600 dark:text-emerald-400">
              {userProfile?.name
                .split(' ')
                .map((n) => n[0])
                .join('')}
            </div>
            <div className="hidden md:block text-left">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[110px]">
                  {userProfile?.name}
                </span>
                {getRoleBadge(userRole)}
              </div>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 hidden md:block" />
          </button>
          <UserProfileMenu isOpen={isProfileOpen} onClose={() => setIsProfileOpen(false)} />
        </div>
      </div>
    </header>
  );
};
