import React from 'react';
import { useApp } from '../../context/AppContext';
import { Settings, User, Bell, Database, Shield, Sliders, Sun, Moon, Check, Laptop } from 'lucide-react';
import { toast } from 'sonner';

export const SettingsView: React.FC = () => {
  const { userProfile, userRole, theme, setTheme } = useApp();

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="pb-4 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
          <Settings className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          <span>Platform Settings & Workspace Preferences</span>
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Manage your interface appearance and analytics display preferences.
        </p>
      </div>

      <div className="space-y-4">
        {/* Theme & Appearance Card */}
        <div className="p-5 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xs">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-2 flex items-center gap-2">
            <Sun className="w-4 h-4 text-amber-500 dark:text-amber-400" />
            <span>Theme & Display Appearance</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
            Select your preferred interface style. NEPSE Insight uses high-contrast dark-first financial styling by default.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-2 gap-3 max-w-md">
            <button
              onClick={() => {
                setTheme('dark');
                toast.success('Dark theme activated');
              }}
              className={`p-3.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                theme === 'dark'
                  ? 'bg-slate-100 dark:bg-slate-800 border-emerald-500 text-slate-900 dark:text-white shadow-xs'
                  : 'bg-white dark:bg-[#0e1422] border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-slate-100 dark:bg-[#0b0f19] border border-slate-200 dark:border-slate-800 text-amber-500 dark:text-amber-400">
                  <Moon className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-900 dark:text-slate-200">Dark Mode</p>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400">Deep navy financial</p>
                </div>
              </div>
              {theme === 'dark' && <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
            </button>

            <button
              onClick={() => {
                setTheme('light');
                toast.success('Light theme activated');
              }}
              className={`p-3.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                theme === 'light'
                  ? 'bg-slate-100 dark:bg-slate-800 border-emerald-500 text-slate-900 dark:text-white shadow-xs'
                  : 'bg-white dark:bg-[#0e1422] border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-sky-600 dark:text-sky-400">
                  <Sun className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-900 dark:text-slate-200">Light Mode</p>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400">Clean slate canvas</p>
                </div>
              </div>
              {theme === 'light' && <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
            </button>
          </div>
        </div>

        {/* User Profile Card */}
        <div className="p-5 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xs">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
            <User className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Profile & Role Authorization</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-slate-700 dark:text-slate-400 block mb-1.5 font-medium">Full Name</label>
              <input
                type="text"
                disabled
                value={userProfile?.name || ''}
                className="w-full bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-200 opacity-80"
              />
            </div>
            <div>
              <label className="text-slate-700 dark:text-slate-400 block mb-1.5 font-medium">Email Address</label>
              <input
                type="text"
                disabled
                value={userProfile?.email || ''}
                className="w-full bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-200 opacity-80"
              />
            </div>
            <div>
              <label className="text-slate-700 dark:text-slate-400 block mb-1.5 font-medium">Active Workspace Role</label>
              <p className="rounded-lg border border-slate-200 px-3 py-2 font-mono uppercase text-emerald-600 dark:border-slate-700 dark:text-emerald-400">
                {userRole}
              </p>
            </div>
            <div>
              <label className="text-slate-700 dark:text-slate-400 block mb-1.5 font-medium">Broker Affiliation</label>
              <input
                type="text"
                disabled
                value={userProfile?.brokerAffiliation || 'Not provided'}
                className="w-full bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-200 opacity-80"
              />
            </div>
          </div>
        </div>

        {/* Market Preferences */}
        <div className="p-5 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xs">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-sky-600 dark:text-sky-400" />
            <span>Market Analytics & Currency Preferences</span>
          </h2>
          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800/80">
              <div>
                <p className="font-medium text-slate-900 dark:text-slate-200">Currency Notation</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Display turnover and market capitalization in South Asian notation (Arba, Cr, Lakh)</p>
              </div>
              <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">Enabled (NPR)</span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800/80">
              <div>
                <p className="font-medium text-slate-900 dark:text-slate-200">Date Format Synchronization</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Synchronize trading session dates with Bikram Sambat (BS) calendar and Nepal Standard Time (UTC+5:45)</p>
              </div>
              <span className="font-mono text-slate-700 dark:text-slate-300">BS + NPT Synchronized</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
