'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ApiCompany, compareCompanies, fetchCompanies } from '../../services/api';
import { PageHeader, EmptyState, LoadingState } from '../../components/ui';
import { GitCompare } from 'lucide-react';

export const ComparisonView: React.FC = () => {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [comparedIds, setComparedIds] = useState<number[]>([]);
  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: () => fetchCompanies(),
  });
  const comparisonQuery = useQuery({
    queryKey: ['company-comparison', comparedIds],
    queryFn: () => compareCompanies(comparedIds),
    enabled: comparedIds.length >= 2,
  });
  const companies = companiesQuery.data?.results ?? [];

  const toggleCompany = (id: number) => {
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : current.length < 10
          ? [...current, id]
          : current,
    );
  };

  return (
    <div className="space-y-5">
      <PageHeader
        title="Company Comparison"
        description="Compare recorded price changes and available behavior indicators. Missing prices and floorsheet values are shown as unavailable."
        icon={GitCompare}
      />
      {companiesQuery.isLoading ? (
        <LoadingState message="Loading company directory…" />
      ) : companiesQuery.isError ? (
        <p role="alert" className="text-sm text-rose-600">
          {companiesQuery.error.message}
        </p>
      ) : companies.length ? (
        <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827]">
          <p className="text-sm text-slate-500">
            Select 2–10 companies ({selectedIds.length} selected).
          </p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {companies.map((company: ApiCompany) => (
              <label
                key={company.id}
                className="flex items-center gap-2 rounded-lg border border-slate-200 p-2 text-sm dark:border-slate-700"
              >
                <input
                  type="checkbox"
                  checked={selectedIds.includes(company.id)}
                  onChange={() => toggleCompany(company.id)}
                />
                <span className="font-mono font-semibold">{company.symbol}</span>
                <span className="truncate text-slate-500">{company.name}</span>
              </label>
            ))}
          </div>
          <button
            disabled={selectedIds.length < 2}
            onClick={() => setComparedIds(selectedIds)}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            Compare recorded data
          </button>
        </section>
      ) : (
        <EmptyState
          title="No companies to compare"
          description="The backend has no company records available."
        />
      )}

      {comparisonQuery.isFetching ? (
        <LoadingState message="Comparing stored market data…" />
      ) : comparisonQuery.isError ? (
        <p role="alert" className="text-sm text-rose-600">
          {comparisonQuery.error.message}
        </p>
      ) : comparisonQuery.data ? (
        <section className="space-y-3">
          <p className="text-xs text-slate-500">
            Period {comparisonQuery.data.period.from} to {comparisonQuery.data.period.to}
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {comparisonQuery.data.companies.map((summary) => (
              <article
                key={summary.company.id}
                className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827]"
              >
                <h2 className="font-semibold">
                  {summary.company.symbol} · {summary.company.name}
                </h2>
                <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                  <Metric label="Price change" value={summary.price_change_percent === null ? 'Unavailable' : `${summary.price_change_percent}%`} />
                  <Metric label="Latest close" value={summary.latest_price?.close ?? 'Unavailable'} />
                  <Metric label="Floorsheet VWAP" value={summary.vwap.available ? summary.vwap.value ?? 'Unavailable' : 'Unavailable'} />
                  <Metric label="Trading volume" value={summary.latest_price?.volume.toLocaleString() ?? 'Unavailable'} />
                </dl>
                {!summary.vwap.available && summary.vwap.limitation && (
                  <p className="mt-3 text-xs text-slate-500">{summary.vwap.limitation}</p>
                )}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
};

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 font-mono font-semibold">{value}</dd>
    </div>
  );
}
