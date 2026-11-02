'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMarketAnalysis } from '../../services/api';

export const MarketTickerBar: React.FC = () => {
  const marketQuery = useQuery({
    queryKey: ['market-analysis'],
    queryFn: fetchMarketAnalysis,
  });
  const snapshot = marketQuery.data?.snapshot;
  const updatedAt = snapshot
    ? new Intl.DateTimeFormat('en-NP', {
        timeZone: 'Asia/Kathmandu',
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(snapshot.updated_at))
    : null;

  return (
    <div className="w-full border-b border-slate-200 bg-slate-100 px-4 py-2 text-xs text-slate-600 transition-colors dark:border-slate-800/80 dark:bg-[#0e1422] dark:text-slate-300">
      {marketQuery.isLoading ? (
        <span>Loading sourced NEPSE market data…</span>
      ) : marketQuery.isError ? (
        <span role="alert">Market data unavailable: {marketQuery.error.message}</span>
      ) : snapshot ? (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
          <span className="font-semibold text-slate-800 dark:text-slate-100">
            NEPSE {formatNumber(snapshot.index_value)}
          </span>
          <span
            className={
              Number(snapshot.index_change_percent) > 0
                ? 'text-emerald-700 dark:text-emerald-400'
                : Number(snapshot.index_change_percent) < 0
                  ? 'text-rose-700 dark:text-rose-400'
                  : ''
            }
          >
            {formatPercent(snapshot.index_change_percent)}
          </span>
          <span>Turnover NPR {formatNumber(snapshot.turnover, 0)}</span>
          <span>
            {snapshot.advancers ?? '—'} advancers · {snapshot.decliners ?? '—'} decliners
          </span>
          <span className="text-slate-500 dark:text-slate-400">
            {snapshot.source} · Updated {updatedAt} NPT
          </span>
        </div>
      ) : (
        <span>
          No sourced index snapshot yet. Market data will appear after a provider
          completes collection.
        </span>
      )}
    </div>
  );
};

function formatNumber(value: string | null, maximumFractionDigits = 2) {
  if (value === null || !Number.isFinite(Number(value))) return '—';
  return Number(value).toLocaleString('en-IN', { maximumFractionDigits });
}

function formatPercent(value: string | null) {
  if (value === null || !Number.isFinite(Number(value))) return '—';
  const numeric = Number(value);
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(2)}%`;
}
