'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ApiCompany,
  ApiMarketLeader,
  ApiMarketAnalysis,
  ApiMarketHistoryRange,
  ApiMarketStock,
  fetchMarketAnalysis,
  fetchCompanies,
  fetchCompanyBehaviorSummary,
} from '../../services/api';
import {
  ChartCard,
  EmptyState,
  LoadingState,
  PageHeader,
  StatCard,
} from '../../components/ui';
import { Activity, TrendingUp } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export const MarketAnalysisView: React.FC = () => {
  const [companyId, setCompanyId] = useState<number | null>(null);
  const [historyRange, setHistoryRange] = useState<ApiMarketHistoryRange>('30d');
  const marketQuery = useQuery({
    queryKey: ['market-analysis', historyRange],
    queryFn: () => fetchMarketAnalysis(historyRange),
    refetchInterval: 5 * 60 * 1000,
  });
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
        description="Quotes and index data are collected from NEPSE Alpha, ShareSansar, and Merolagani. Bizmandu provides market news but no structured quote feed."
        icon={TrendingUp}
      />
      {marketQuery.isLoading ? (
        <LoadingState message="Loading NEPSE market data…" />
      ) : marketQuery.isError ? (
        <p role="alert" className="text-sm text-rose-600">
          {marketQuery.error.message}
        </p>
      ) : marketQuery.data?.snapshot ? (
        <NepseMarketOverview
          data={marketQuery.data}
          range={historyRange}
          onRangeChange={setHistoryRange}
        />
      ) : marketQuery.data?.history.length ? (
        <HistoricalIndexOnly
          data={marketQuery.data}
          range={historyRange}
          onRangeChange={setHistoryRange}
        />
      ) : (
        <EmptyState
          title="Market data is not available yet"
          description="No configured provider has saved a market snapshot yet. Data will appear after the next successful collection."
          icon={Activity}
          className="max-w-none"
        />
      )}
      {marketQuery.data?.stocks.length ? (
        <MarketStockTable stocks={marketQuery.data.stocks} />
      ) : marketQuery.isSuccess && marketQuery.data?.snapshot ? (
        <EmptyState
          title="No stock quotes are available"
          description="The selected market sources have not returned stock quote rows."
        />
      ) : null}
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

function HistoricalIndexOnly({
  data,
  range,
  onRangeChange,
}: {
  data: ApiMarketAnalysis;
  range: ApiMarketHistoryRange;
  onRangeChange: (range: ApiMarketHistoryRange) => void;
}) {
  const chartData = data.history
    .map((point) => ({
      time: Date.parse(`${point.date}T00:00:00+05:45`),
      value: Number(point.value),
    }))
    .filter((point) => Number.isFinite(point.time) && Number.isFinite(point.value));
  const historyPeriod = data.history_period;
  const updatedAt = historyPeriod.updated_at
    ? new Intl.DateTimeFormat('en-NP', {
        timeZone: 'Asia/Kathmandu',
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(historyPeriod.updated_at))
    : 'Unavailable';

  return (
    <ChartCard
      title="NEPSE historical performance"
      subtitle={`${historyPeriod.from ?? 'Unavailable'} – ${historyPeriod.to ?? 'Unavailable'} · Change ${historyPeriod.change_percent === null ? 'unavailable' : `${historyPeriod.change_percent}%`}`}
      footer={`Available data: ${historyPeriod.available_from ?? 'Unavailable'} – ${historyPeriod.available_to ?? 'Unavailable'} · Last updated ${updatedAt} NPT`}
      actions={
        <label className="flex items-center gap-2 text-xs text-slate-500">
          History
          <select
            value={range}
            onChange={(event) =>
              onRangeChange(event.target.value as ApiMarketHistoryRange)
            }
            className="rounded border border-slate-300 bg-transparent px-2 py-1 text-slate-900 dark:border-slate-700 dark:text-slate-100"
            aria-label="NEPSE historical date range"
          >
            <option value="7d">7 days</option>
            <option value="15d">15 days</option>
            <option value="30d">30 days</option>
            <option value="90d">90 days</option>
            <option value="180d">180 days</option>
            <option value="1y">1 year</option>
            <option value="all">All available</option>
          </select>
        </label>
      }
    >
      {chartData.length ? (
        <div className="h-64 w-full min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.45} />
              <XAxis
                dataKey="time"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                minTickGap={36}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(value: number) => formatHistoryTick(value, '')}
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(value: number) => formatMarketNumber(String(value))}
                width={64}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#111827',
                  borderColor: '#334155',
                  color: '#e2e8f0',
                }}
                labelFormatter={(value) =>
                  new Intl.DateTimeFormat('en-NP', {
                    timeZone: 'Asia/Kathmandu',
                    dateStyle: 'medium',
                  }).format(new Date(Number(value)))
                }
                formatter={(value) => [formatMarketNumber(String(value)), 'NEPSE']}
              />
              <Area
                type="monotone"
                dataKey="value"
                name="NEPSE"
                stroke="#10b981"
                strokeWidth={2}
                fill="#10b981"
                fillOpacity={0.15}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState
          title="Index history is unavailable"
          description="No provider-supplied historical index values are available for this range."
          className="max-w-none"
        />
      )}
    </ChartCard>
  );
}

function NepseMarketOverview({
  data,
  range,
  onRangeChange,
}: {
  data: ApiMarketAnalysis;
  range: ApiMarketHistoryRange;
  onRangeChange: (range: ApiMarketHistoryRange) => void;
}) {
  const snapshot = data.snapshot;
  if (!snapshot) return null;

  const chartData = [
    ...data.history.map((point) => ({
      time: Date.parse(`${point.date}T00:00:00+05:45`),
      value: Number(point.value),
    })),
    ...data.intraday.map((point) => ({
      time: Date.parse(point.observed_at),
      value: Number(point.value),
    })),
  ]
    .filter((point) => Number.isFinite(point.time) && Number.isFinite(point.value))
    .sort((left, right) => left.time - right.time);
  const marketStatus =
    snapshot.market_open === null
      ? 'Status unavailable'
      : snapshot.market_open
        ? 'Market open'
        : 'Market closed';
  const updatedAt = new Intl.DateTimeFormat('en-NP', {
    timeZone: 'Asia/Kathmandu',
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(snapshot.updated_at));
  const technical = snapshot.technical_indicators;
  const technicalSummary = asRecord(technical.summary);
  const indicatorGroups = asRecord(technical.indicators);
  const historyPeriod = data.history_period;
  const availableRange =
    historyPeriod.available_from && historyPeriod.available_to
      ? `${historyPeriod.available_from} – ${historyPeriod.available_to}`
      : 'Unavailable';
  const historyUpdatedAt = historyPeriod.updated_at
    ? new Intl.DateTimeFormat('en-NP', {
        timeZone: 'Asia/Kathmandu',
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(historyPeriod.updated_at))
    : 'Unavailable';

  return (
    <section className="space-y-4" aria-label="NEPSE market overview">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold">
          NEPSE market overview · {snapshot.source}
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-500">
            History
            <select
              value={range}
              onChange={(event) =>
                onRangeChange(event.target.value as ApiMarketHistoryRange)
              }
              className="rounded border border-slate-300 bg-transparent px-2 py-1 text-slate-900 dark:border-slate-700 dark:text-slate-100"
              aria-label="NEPSE historical date range"
            >
              <option value="7d">7 days</option>
              <option value="15d">15 days</option>
              <option value="30d">30 days</option>
              <option value="90d">90 days</option>
              <option value="180d">180 days</option>
              <option value="1y">1 year</option>
              <option value="all">All available</option>
            </select>
          </label>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {marketStatus} · Updated {updatedAt} NPT
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="NEPSE Index"
          value={formatMarketNumber(snapshot.index_value)}
          change={
            snapshot.index_change_percent === null
              ? undefined
              : Number(snapshot.index_change_percent)
          }
          subtext={
            snapshot.previous_close === null
              ? 'Previous close unavailable'
              : `Previous close ${formatMarketNumber(snapshot.previous_close)}`
          }
        />
        <StatCard
          title="Market Turnover"
          value={formatMarketNumber(snapshot.turnover, 0)}
          subtext="NPR"
        />
        <StatCard
          title="Shares Traded"
          value={formatMarketNumber(snapshot.traded_volume, 0)}
          subtext={
            snapshot.transaction_count === null
              ? 'Transaction count unavailable'
              : `${snapshot.transaction_count.toLocaleString('en-IN')} transactions`
          }
        />
        <StatCard
          title="Market Breadth"
          value={`${snapshot.advancers ?? '—'} / ${snapshot.decliners ?? '—'} / ${snapshot.unchanged ?? '—'}`}
          subtext="Advancers / decliners / unchanged"
        />
      </div>

      <ChartCard
        title="NEPSE historical performance"
        subtitle={`${historyPeriod.from ?? 'Unavailable'} – ${historyPeriod.to ?? 'Unavailable'} · Change ${historyPeriod.change_percent === null ? 'unavailable' : `${historyPeriod.change_percent}%`}`}
        footer={`Available data: ${availableRange} · Last updated ${historyUpdatedAt} NPT`}
      >
        {chartData.length ? (
          <div className="h-64 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="nepseIndexFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.28} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.45} />
              <XAxis
                dataKey="time"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                minTickGap={36}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(value: number) =>
                  formatHistoryTick(value, snapshot.date)
                }
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                tickFormatter={(value: number) => formatMarketNumber(String(value))}
                width={64}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#111827',
                  borderColor: '#334155',
                  color: '#e2e8f0',
                }}
                labelFormatter={(value) =>
                  new Intl.DateTimeFormat('en-NP', {
                    timeZone: 'Asia/Kathmandu',
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  }).format(new Date(Number(value)))
                }
                formatter={(value) => [formatMarketNumber(String(value)), 'NEPSE']}
              />
              <Area
                type="monotone"
                dataKey="value"
                name="NEPSE"
                stroke="#10b981"
                strokeWidth={2}
                fill="url(#nepseIndexFill)"
                isAnimationActive={false}
                connectNulls
              />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            title="Index history is unavailable"
            description="The selected source has not supplied historical index points for this snapshot."
            className="max-w-none"
          />
        )}
      </ChartCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827]">
          <h3 className="mb-3 text-sm font-semibold">Indices and sector performance</h3>
          {data.indices.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-slate-500 dark:text-slate-400">
                  <tr>
                    <th className="pb-2 font-medium">Sector</th>
                    <th className="pb-2 text-right font-medium">Index</th>
                    <th className="pb-2 text-right font-medium">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {data.indices.map((sector) => (
                    <tr
                      key={`${sector.symbol}-${sector.is_sector ? 'sector' : 'index'}`}
                      className="border-t border-slate-100 dark:border-slate-800"
                    >
                      <td className="py-2">
                        <span className="font-medium">{sector.name}</span>
                        <span className="ml-2 text-xs text-slate-500">
                          {sector.symbol}{sector.is_sector ? ' · Sector' : ''}
                        </span>
                      </td>
                      <td className="py-2 text-right font-mono">
                        {formatMarketNumber(sector.close_value)}
                      </td>
                      <td
                        className={`py-2 text-right font-mono ${
                          Number(sector.change_percent) > 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : Number(sector.change_percent) < 0
                              ? 'text-rose-600 dark:text-rose-400'
                              : 'text-slate-500'
                        }`}
                      >
                        {formatPercentValue(sector.change_percent)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Index and sector data is unavailable.</p>
          )}
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827]">
          <h3 className="mb-3 text-sm font-semibold">Technical indicators</h3>
          {Object.keys(technicalSummary).length || Object.keys(indicatorGroups).length ? (
            <div className="space-y-3">
              {Object.keys(technicalSummary).length > 0 && (
                <div className="grid gap-2 sm:grid-cols-3">
                  {Object.entries(technicalSummary).map(([name, value]) => {
                    const summary = asRecord(value);
                    return (
                      <div
                        key={name}
                        className="rounded-lg bg-slate-50 p-2 text-xs dark:bg-slate-900/70"
                      >
                        <span className="text-slate-500 dark:text-slate-400">
                          {name.replace(/_/g, ' ')}
                        </span>
                        <p className="mt-1 font-semibold">
                          {displayIndicator(summary.action ?? value)}
                        </p>
                        {summary.value !== undefined && (
                          <p className="mt-1 font-mono text-slate-500">
                            Score {displayIndicator(summary.value)}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
              {Object.entries(indicatorGroups).map(([group, values]) => (
                <div key={group}>
                  <h4 className="mb-1 text-xs font-semibold capitalize text-slate-500 dark:text-slate-400">
                    {group.replace(/_/g, ' ')}
                  </h4>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {indicatorEntries(values).map(([name, value]) => (
                      <div
                        key={name}
                        className="rounded-lg bg-slate-50 p-2 text-xs dark:bg-slate-900/70"
                      >
                        <span className="text-slate-500 dark:text-slate-400">
                          {name.replace(/_/g, ' ')}
                        </span>
                        <p className="mt-1 break-words font-medium">
                          {displayIndicator(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              <details className="text-xs text-slate-500 dark:text-slate-400">
                <summary className="cursor-pointer">View complete provider response</summary>
                <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-3 dark:bg-slate-900">
                  {JSON.stringify(technical, null, 2)}
                </pre>
              </details>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              No technical indicators were returned with this provider's snapshot.
            </p>
          )}
        </section>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <LeaderList
          title="Top gainers"
          leaders={snapshot.top_gainers}
          valueKey="change_percent"
          valueLabel="Change"
        />
        <LeaderList
          title="Top losers"
          leaders={snapshot.top_losers}
          valueKey="change_percent"
          valueLabel="Change"
        />
        <LeaderList
          title="Top traded"
          leaders={snapshot.top_traded}
          valueKey="turnover_crore"
          valueLabel="Turnover (Cr)"
        />
      </div>
    </section>
  );
}

function MarketStockTable({ stocks }: { stocks: ApiMarketStock[] }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827]">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold">Latest stock quotes</h2>
        <p className="text-xs text-slate-500">
          Per-provider latest snapshots · {stocks.length} rows
        </p>
      </div>
      <div className="max-h-[32rem] overflow-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="sticky top-0 bg-slate-50 text-xs text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            <tr>
              <th className="p-2 font-medium">Symbol</th>
              <th className="p-2 font-medium">Source</th>
              <th className="p-2 text-right font-medium">Open</th>
              <th className="p-2 text-right font-medium">High</th>
              <th className="p-2 text-right font-medium">Low</th>
              <th className="p-2 text-right font-medium">LTP</th>
              <th className="p-2 text-right font-medium">Change</th>
              <th className="p-2 text-right font-medium">Volume</th>
              <th className="p-2 text-right font-medium">Turnover (NPR)</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock) => (
              <tr
                key={`${stock.source}-${stock.date}-${stock.symbol}`}
                className="border-t border-slate-100 dark:border-slate-800"
              >
                <td className="p-2 font-mono font-semibold">{stock.symbol}</td>
                <td className="p-2 text-xs text-slate-500">{stock.source}</td>
                <td className="p-2 text-right font-mono">
                  {formatMarketNumber(stock.open_price)}
                </td>
                <td className="p-2 text-right font-mono">
                  {formatMarketNumber(stock.high_price)}
                </td>
                <td className="p-2 text-right font-mono">
                  {formatMarketNumber(stock.low_price)}
                </td>
                <td className="p-2 text-right font-mono">
                  {formatMarketNumber(stock.close_price)}
                </td>
                <td
                  className={`p-2 text-right font-mono ${
                    Number(stock.change_percent) > 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : Number(stock.change_percent) < 0
                        ? 'text-rose-600 dark:text-rose-400'
                        : 'text-slate-500'
                  }`}
                >
                  {formatPercentValue(stock.change_percent)}
                </td>
                <td className="p-2 text-right font-mono">
                  {formatMarketNumber(stock.volume, 0)}
                </td>
                <td className="p-2 text-right font-mono">
                  {formatMarketNumber(stock.turnover, 0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function LeaderList({
  title,
  leaders,
  valueKey,
  valueLabel,
}: {
  title: string;
  leaders: ApiMarketLeader[];
  valueKey: 'change_percent' | 'turnover_crore';
  valueLabel: string;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827]">
      <h3 className="mb-3 text-sm font-semibold">{title}</h3>
      {leaders.length ? (
        <ul className="space-y-2">
          {leaders.map((leader) => (
            <li
              key={leader.symbol}
              className="flex items-center justify-between gap-3 border-t border-slate-100 pt-2 first:border-0 first:pt-0 dark:border-slate-800"
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">{leader.symbol}</span>
                <span className="block truncate text-xs text-slate-500">{leader.name}</span>
              </span>
              <span className="shrink-0 text-right">
                <span className="block text-xs text-slate-500">{valueLabel}</span>
                <span className="font-mono text-sm">
                  {valueKey === 'change_percent'
                    ? formatPercentValue(leader[valueKey])
                    : formatMarketNumber(
                        leader[valueKey] === undefined || leader[valueKey] === null
                          ? null
                          : String(leader[valueKey]),
                      )}
                </span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">Provider data is unavailable.</p>
      )}
    </section>
  );
}

function formatMarketNumber(value: string | null, maximumFractionDigits = 2) {
  if (value === null || !Number.isFinite(Number(value))) return '—';
  return Number(value).toLocaleString('en-IN', { maximumFractionDigits });
}

function formatHistoryTick(value: number, snapshotDate: string) {
  const date = new Date(value);
  const datePart = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kathmandu',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
  return datePart === snapshotDate
    ? new Intl.DateTimeFormat('en-NP', {
        timeZone: 'Asia/Kathmandu',
        hour: '2-digit',
        minute: '2-digit',
      }).format(date)
    : new Intl.DateTimeFormat('en-NP', {
        timeZone: 'Asia/Kathmandu',
        month: 'short',
        day: 'numeric',
      }).format(date);
}

function formatPercentValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return '—';
  }
  const numeric = Number(value);
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(2)}%`;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function displayIndicator(value: unknown) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  const record = asRecord(value);
  if ('value' in record || 'action' in record) {
    return [record.value, record.action]
      .filter((part) => part !== undefined && part !== null)
      .map(String)
      .join(' · ');
  }
  return JSON.stringify(value);
}

function indicatorEntries(value: unknown): Array<[string, unknown]> {
  if (Array.isArray(value)) {
    return value.map((item, index) => {
      const name = asRecord(item).name;
      return [typeof name === 'string' ? name : String(index + 1), item];
    });
  }
  return Object.entries(asRecord(value));
}

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
