import React, { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { TopNavigation } from './TopNavigation';
import { MarketTickerBar } from './MarketTickerBar';
import { Sidebar } from './Sidebar';
import { GlobalSearchDialog } from './GlobalSearchDialog';
import { useApp } from '../../context/AppContext';
import { Toaster } from 'sonner';
import { toast } from 'sonner';
import { wsService } from '../../services/websocket';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const { activeTab, selectedCompany, theme } = useApp();
  const queryClient = useQueryClient();

  useEffect(() => {
    wsService.connect();
    const unsubscribe = wsService.subscribe((update) => {
      if (update.event.startsWith('news.')) {
        void queryClient.invalidateQueries({ queryKey: ['news'] });
        if (update.event === 'news.article.created') {
          toast.info('New market news collected.');
        }
      }
      if (update.event.startsWith('market.')) {
        void queryClient.invalidateQueries({ queryKey: ['companies'] });
        void queryClient.invalidateQueries({ queryKey: ['company-prices'] });
        void queryClient.invalidateQueries({ queryKey: ['company-behavior'] });
      }
      if (update.event.startsWith('crawl.')) {
        void queryClient.invalidateQueries({ queryKey: ['crawl-runs'] });
      }
    });

    return () => {
      unsubscribe();
      wsService.disconnect();
    };
  }, [queryClient]);

  const getBreadcrumbTitle = () => {
    switch (activeTab) {
      case 'overview':
        return 'Market Overview & Real-Time Pulse';
      case 'companies':
        return selectedCompany
          ? `Company Details · ${selectedCompany.symbol} (${selectedCompany.name})`
          : 'Listed Companies Directory';
      case 'market-analysis':
        return 'Market Analysis & VWAP Pressure Engine';
      case 'news-intelligence':
        return 'Financial News Intelligence & Categorization';
      case 'comparison':
        return 'Cross-Company Comparative Analytics';
      case 'admin-panel':
        return 'Crawler Monitoring & Administration Console';
      case 'settings':
        return 'Platform Settings & Account Configuration';
      default:
        return 'NEPSE Insight';
    }
  };

  return (
    <div className="min-h-screen min-w-0 bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 flex flex-col font-sans transition-colors duration-200">
      <Toaster
        theme={theme}
        position="top-right"
      />

      {/* Primary Top Bar */}
      <TopNavigation />

      {/* Live Market Indices Ticker Bar */}
      <MarketTickerBar />

      {/* Main Workspace Body */}
      <div className="flex-1 min-w-0 flex">
        {/* Reusable Sidebar */}
        <Sidebar />

        {/* Viewport Canvas */}
        <main className="flex-1 flex flex-col min-w-0 bg-slate-50 dark:bg-[#0B0F19] overflow-x-clip overflow-y-auto">
          {/* Breadcrumb / Section Header Strip */}
          <div className="px-3 sm:px-4 md:px-8 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-white dark:bg-[#0e1422]/60 flex items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-2 text-xs">
              <span className="text-slate-400">NEPSE</span>
              <span className="text-slate-400">/</span>
              <span className="min-w-0 font-semibold text-slate-700 dark:text-slate-200 break-words">{getBreadcrumbTitle()}</span>
            </div>
            <div className="hidden sm:flex items-center gap-3 text-xs text-slate-400">
              <span className="font-mono">Exchange: NEPSE (Kathmandu)</span>
              <span>·</span>
              <span className="text-emerald-500 font-mono">Currency: NPR</span>
            </div>
          </div>

          {/* Page Content View */}
          <div className="flex-1 min-w-0 w-full max-w-7xl mx-auto p-3 sm:p-4 md:p-8">
            {children}
          </div>
        </main>
      </div>

      {/* Global Cmd+K Search Modal */}
      <GlobalSearchDialog />
    </div>
  );
};
