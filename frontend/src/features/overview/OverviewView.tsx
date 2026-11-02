'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useApp } from '../../context/AppContext';
import {
  ApiCompany,
  ApiNewsArticle,
  fetchCompanies,
  fetchMarketAnalysis,
  fetchNews,
} from '../../services/api';
import {
  DataTable,
  EmptyState,
  LoadingState,
  PageHeader,
  StatCard,
  StatusBadge,
} from '../../components/ui';
import { Column } from '../../components/ui/DataTable';
import { Building2, Newspaper, Activity } from 'lucide-react';

export const OverviewView: React.FC = () => {
  const { setActiveTab } = useApp();
  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: () => fetchCompanies(),
  });
  const newsQuery = useQuery({
    queryKey: ['news'],
    queryFn: () => fetchNews(),
  });
  const marketQuery = useQuery({
    queryKey: ['market-analysis'],
    queryFn: fetchMarketAnalysis,
  });
  const companies = companiesQuery.data?.results ?? [];
  const articles = newsQuery.data ?? [];
  const marketSnapshot = marketQuery.data?.snapshot;
  const companyColumns: Column<ApiCompany>[] = [
    {
      key: 'symbol',
      header: 'Symbol',
      render: (company) => (
        <span className="font-mono font-semibold">{company.symbol}</span>
      ),
    },
    { key: 'name', header: 'Company' },
    { key: 'sector', header: 'Sector' },
  ];

  return (
    <div className="space-y-5">
      <PageHeader
        title="NEPSE Insight Dashboard"
        description="Sourced market, company, and collected-news records from configured providers."
        badge={<StatusBadge label="Source-backed data only" variant="info" />}
        actions={
          <button
            onClick={() => setActiveTab('market-analysis')}
            className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white"
          >
            View market analysis
          </button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Company records"
          value={
            companiesQuery.data
              ? companiesQuery.data.count.toLocaleString()
              : companiesQuery.isLoading
                ? 'Loading'
                : 'Unavailable'
          }
          icon={Building2}
          iconColor="text-sky-400"
          subtext="Company directory entries"
        />
        <StatCard
          title="Recent collected articles"
          value={newsQuery.isLoading ? 'Loading' : articles.length.toLocaleString()}
          icon={Newspaper}
          iconColor="text-emerald-400"
          subtext="Articles in the current API page"
        />
        <StatCard
          title="Market index"
          value={
            marketQuery.isLoading
              ? 'Loading'
              : marketSnapshot?.index_value
                ? Number(marketSnapshot.index_value).toLocaleString('en-IN', {
                    maximumFractionDigits: 2,
                  })
                : 'Unavailable'
          }
          icon={Activity}
          iconColor="text-amber-400"
          change={
            marketSnapshot?.index_change_percent == null
              ? undefined
              : Number(marketSnapshot.index_change_percent)
          }
          subtext={
            marketSnapshot
              ? `${marketSnapshot.source} · ${marketSnapshot.date}`
              : marketQuery.isError
                ? marketQuery.error.message
                : 'No sourced index snapshot yet'
          }
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Company directory</h2>
            <button
              onClick={() => setActiveTab('companies')}
              className="text-xs text-emerald-600 hover:underline"
            >
              Open companies
            </button>
          </div>
          {companiesQuery.isLoading ? (
            <LoadingState message="Loading company records…" />
          ) : companiesQuery.isError ? (
            <p role="alert" className="text-sm text-rose-600">
              {companiesQuery.error.message}
            </p>
          ) : companies.length ? (
            <DataTable
              columns={companyColumns}
              data={companies.slice(0, 8)}
              keyExtractor={(company) => company.id}
            />
          ) : (
            <EmptyState
              title="No company records"
              description="The directory has no records yet."
            />
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Collected news</h2>
            <button
              onClick={() => setActiveTab('news-intelligence')}
              className="text-xs text-emerald-600 hover:underline"
            >
              Open news intelligence
            </button>
          </div>
          {newsQuery.isLoading ? (
            <LoadingState message="Loading collected news…" />
          ) : newsQuery.isError ? (
            <p role="alert" className="text-sm text-rose-600">
              {newsQuery.error.message}
            </p>
          ) : articles.length ? (
            <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white dark:divide-slate-800 dark:border-slate-800 dark:bg-[#111827]">
              {articles.slice(0, 8).map((article: ApiNewsArticle) => (
                <li key={article.id} className="p-3">
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-medium hover:text-emerald-600"
                  >
                    {article.headline}
                  </a>
                  <p className="mt-1 text-[11px] text-slate-500">
                    {article.source} ·{' '}
                    {article.published_at
                      ? new Date(article.published_at).toLocaleString()
                      : 'Publication date unavailable'}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No collected articles"
              description="News will appear after a configured source completes a successful crawl."
            />
          )}
        </section>
      </div>
    </div>
  );
};
