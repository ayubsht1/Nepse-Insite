/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

'use client';

import React from 'react';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider, useApp } from './context/AppContext';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { OverviewView } from './features/overview/OverviewView';
import { CompaniesView } from './features/companies/CompaniesView';
import { MarketAnalysisView } from './features/market-analysis/MarketAnalysisView';
import { NewsIntelligenceView } from './features/news/NewsIntelligenceView';
import { ComparisonView } from './features/comparison/ComparisonView';
import { AdminPanelView } from './features/admin/AdminPanelView';
import { SettingsView } from './features/settings/SettingsView';
import { NavigationTab, UserRole } from './types';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5, // 5 minutes
    },
  },
});

const ContentSwitcher: React.FC = () => {
  const { activeTab } = useApp();

  switch (activeTab) {
    case 'overview':
      return <OverviewView />;
    case 'companies':
      return <CompaniesView />;
    case 'market-analysis':
      return <MarketAnalysisView />;
    case 'news-intelligence':
      return <NewsIntelligenceView />;
    case 'comparison':
      return <ComparisonView />;
    case 'admin-panel':
      return <AdminPanelView />;
    case 'settings':
      return <SettingsView />;
    default:
      return <OverviewView />;
  }
};

function AuthenticatedDashboard({
  requiredRole,
}: {
  requiredRole?: 'admin' | 'analyst';
}) {
  const router = useRouter();
  const { authLoading, authError, userProfile } = useApp();

  useEffect(() => {
    if (!authLoading && !userProfile) {
      router.replace('/login');
    }
  }, [authLoading, router, userProfile]);

  if (authLoading || !userProfile) {
    return (
      <main className="min-h-screen flex items-center justify-center text-sm text-slate-500">
        {authError || 'Checking your NEPSE Insight session…'}
      </main>
    );
  }

  const allowed =
    !requiredRole ||
    userProfile.role === 'admin' ||
    userProfile.role === requiredRole;
  if (!allowed) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6 text-center">
        <div>
          <h1 className="text-xl font-semibold">Access denied</h1>
          <p className="mt-2 text-sm text-slate-500">
            This page requires the {requiredRole} role. Your account is {userProfile.role}.
          </p>
          <button
            className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white"
            onClick={() => router.replace('/dashboard')}
          >
            Go to dashboard
          </button>
        </div>
      </main>
    );
  }

  return (
    <DashboardLayout>
      <ContentSwitcher />
    </DashboardLayout>
  );
}

export default function App({
  initialTab = 'overview',
  requiredRole,
}: {
  initialTab?: NavigationTab;
  requiredRole?: 'admin' | 'analyst';
}) {
  return (
    <QueryClientProvider client={queryClient}>
      <AppProvider initialTab={initialTab}>
        <AuthenticatedDashboard requiredRole={requiredRole} />
      </AppProvider>
    </QueryClientProvider>
  );
}
