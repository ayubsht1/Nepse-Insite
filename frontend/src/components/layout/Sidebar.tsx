import React from 'react';
import { useApp } from '../../context/AppContext';
import { NavigationTab } from '../../types';
import {
  LayoutDashboard,
  Building2,
  TrendingUp,
  Newspaper,
  GitCompare,
  ShieldCheck,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Lock,
} from 'lucide-react';
import { toast } from 'sonner';

interface NavItem {
  id: NavigationTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
}

export const Sidebar: React.FC = () => {
  const {
    activeTab,
    setActiveTab,
    userRole,
    sidebarCollapsed,
    setSidebarCollapsed,
    mobileMenuOpen,
    setMobileMenuOpen,
    handleLogout,
  } = useApp();

  const navItems: NavItem[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'companies', label: 'Companies', icon: Building2 },
    { id: 'market-analysis', label: 'Market Analysis', icon: TrendingUp },
    { id: 'news-intelligence', label: 'News Intelligence', icon: Newspaper },
    { id: 'comparison', label: 'Comparison', icon: GitCompare },
    { id: 'admin-panel', label: 'Admin Panel', icon: ShieldCheck, adminOnly: true },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const handleNavClick = (item: NavItem) => {
    if (item.adminOnly && userRole !== 'admin') {
      toast.error('Access Restricted', {
        description: 'Admin Panel requires administrator credentials. Switch role in user profile.',
      });
      return;
    }
    setActiveTab(item.id);
    setMobileMenuOpen(false);
  };

  const onLogoutClick = async () => {
    try {
      await handleLogout();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to log out.');
    }
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/70 z-40 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:sticky top-0 md:top-16 z-50 md:z-30 h-screen md:h-[calc(100vh-4rem)] w-64 shrink-0 bg-white dark:bg-[#0e1422] border-r border-slate-200 dark:border-slate-800/90 flex flex-col justify-between transition-all duration-200 select-none ${
          sidebarCollapsed ? 'md:w-16' : 'md:w-64'
        } ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
      >
        {/* Top: Mobile header or branding */}
        <div className="flex flex-col flex-1 overflow-y-auto">
          {/* Mobile title */}
          <div className="md:hidden flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#111827]">
            <span className="font-bold text-slate-900 dark:text-white text-base">
              NEPSE <span className="text-emerald-500 dark:text-emerald-400">Insight</span>
            </span>
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links List */}
          <nav className="p-2.5 space-y-1">
            <div className={`px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400 ${
              sidebarCollapsed && !mobileMenuOpen ? 'hidden' : 'block'
            }`}>
              Platform Navigation
            </div>

            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              const isLocked = item.adminOnly && userRole !== 'admin';

              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item)}
                  title={sidebarCollapsed ? item.label : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/20 shadow-sm'
                      : isLocked
                      ? 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/30'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/50'
                  } ${sidebarCollapsed ? 'justify-center px-0' : ''}`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-emerald-500 dark:text-emerald-400' : 'text-slate-400'}`} />
                  
                  {(!sidebarCollapsed || mobileMenuOpen) && (
                    <span className="flex-1 text-left truncate">{item.label}</span>
                  )}

                  {(!sidebarCollapsed || mobileMenuOpen) && item.adminOnly && (
                    isLocked ? (
                      <Lock className="w-3.5 h-3.5 text-slate-400" />
                    ) : (
                      <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-400 dark:border-emerald-800/50">
                        ADMIN
                      </span>
                    )
                  )}
                </button>
              );
            })}
          </nav>

        </div>

        {/* Bottom Section: Logout + Collapse Button */}
        <div className="p-2.5 border-t border-slate-200 dark:border-slate-800/90 space-y-1 bg-white dark:bg-[#0b0f19]">
          <button
            onClick={onLogoutClick}
            title={sidebarCollapsed ? 'Logout' : undefined}
            className={`w-full flex items-center gap-3 px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/20 rounded-lg transition-colors ${
              sidebarCollapsed ? 'justify-center px-0' : ''
            }`}
          >
            <LogOut className="w-4 h-4 shrink-0 text-slate-400" />
            {(!sidebarCollapsed || mobileMenuOpen) && <span>Logout</span>}
          </button>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={() => setSidebarCollapsed((prev) => !prev)}
            className="hidden md:flex w-full items-center justify-center p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <ChevronLeft className="w-4 h-4" />
                <span>Collapse Sidebar</span>
              </div>
            )}
          </button>
        </div>
      </aside>
    </>
  );
};
