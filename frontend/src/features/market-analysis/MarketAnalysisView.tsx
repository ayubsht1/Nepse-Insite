'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ApiCompany,
  fetchCompanies,
  fetchCompanyBehaviorSummary,
} from '../../services/api';
import { EmptyState, LoadingState, PageHeader } from '../../components/ui';
import { TrendingUp } from 'lucide-react';

export const MarketAnalysisView: React.FC = () => {
  const [companyId, setCompanyId] = useState<number | null>(null);
  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: () => fetchCompanies(),
  });
  const companies = companiesQuery.data?.results ?? [];
  const selectedCompany = companies.find((company) => company.id === companyId);
  const analysisQuery = useQuery({
    queryKey: ['company-behavior', companyId, '30d'],
    queryFn: () => fetchCompanyBehaviorSummary(companyId!),
    enabled: companyId !== null,
  });
  const analysis = analysisQuery.data;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Market Analysis"
        description="VWAP uses stored transaction-level floorsheet data. Pressure is a close-location estimate, not actual buyer/seller volume. Volume anomalies require 20 prior trading records."
        icon={TrendingUp}
      />
      {companiesQuery.isLoading ? (
        <LoadingState message="Loading companies…" />
      ) : companiesQuery.isError ? (
        <p role="alert" className="text-sm text-rose-600">
          {companiesQuery.error.message}
        </p>
      ) : companies.length ? (
        <label className="block max-w-xl text-sm">
          Company
          <select
            value={companyId ?? ''}
            onChange={(event) =>
              setCompanyId(event.target.value ? Number(event.target.value) : null)
            }
            className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
          >
            <option value="">Select a company</option>
            {companies.map((company: ApiCompany) => (
              <option key={company.id} value={company.id}>
                {company.symbol} · {company.name}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <EmptyState
          title="No companies available"
          description="Market analysis requires a company record."
        />
      )}

      {analysisQuery.isLoading && <LoadingState message="Loading recorded analysis…" />}
      {analysisQuery.isError && (
        <p role="alert" className="text-sm text-rose-600">
          {analysisQuery.error.message}
        </p>
      )}
      {analysis && (
        <div className="space-y-4">
          <h2 className="font-semibold">
            {selectedCompany?.symbol} · {analysis.period.from} – {analysis.period.to}
          </h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <AnalysisCard
              title="Transaction VWAP"
              value={
                analysis.vwap.available
                  ? analysis.vwap.value ?? 'Unavailable'
                  : 'Unavailable'
              }
              detail={
                analysis.vwap.available
                  ? `${analysis.vwap.transactions} floorsheet transactions`
                  : analysis.vwap.limitation
              }
            />
            <AnalysisCard
              title="Close-location pressure"
              value={
                analysis.latest_pressure_indicator.available
                  ? analysis.latest_pressure_indicator.score ?? 'Unavailable'
                  : 'Unavailable'
              }
              detail={analysis.latest_pressure_indicator.interpretation}
            />
            <AnalysisCard
              title="Volume anomaly"
              value={
                analysis.latest_volume_anomaly.available
                  ? analysis.latest_volume_anomaly.is_anomaly
                    ? 'Detected'
                    : 'Not detected'
                  : 'Unavailable'
              }
              detail={
                analysis.latest_volume_anomaly.available
                  ? `Current volume / ${analysis.latest_volume_anomaly.prior_trading_days}-session average: ${analysis.latest_volume_anomaly.ratio_to_average ?? 'N/A'}×`
                  : analysis.latest_volume_anomaly.reason
              }
            />
            <AnalysisCard
              title="Broker breakdown"
              value={
                analysis.floorsheet.brokers.available
                  ? `${analysis.floorsheet.brokers.brokers.length} broker codes`
                  : 'Unavailable'
              }
              detail={analysis.floorsheet.brokers.limitation}
            />
            <AnalysisCard
              title="News and next trading session"
              value={`${analysis.news_relationship.observations.length} observations`}
              detail={`${analysis.news_relationship.method} ${analysis.news_relationship.limitation}`}
            />
          </div>
        </div>
      )}
    </div>
  );
};

function AnalysisCard({
  title,
  value,
  detail,
}: {
  title: string;
  value: string;
  detail?: string | null;
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827]">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 font-mono text-lg font-bold">{value}</p>
      {detail && <p className="mt-2 text-xs leading-relaxed text-slate-500">{detail}</p>}
    </article>
  );
}
