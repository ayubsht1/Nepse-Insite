'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ApiCompany,
  ApiMarketLeader,
  ApiMarketHistoryRange,
  fetchCompanies,
  fetchCompanyBehaviorSummary,
  fetchCompanyFloorsheet,
  fetchCompanyPrices,
  fetchMarketAnalysis,
} from '../../services/api';
import { useApp } from '../../context/AppContext';
import { DataTable, EmptyState, LoadingState, PageHeader } from '../../components/ui';
import { Column } from '../../components/ui/DataTable';
import { Building2 } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

export const CompaniesView: React.FC = () => {
  const { selectedCompanyId, setSelectedCompanyId } = useApp();
  const [search, setSearch] = useState('');
  const [sector, setSector] = useState('');
  const [selectedCompany, setSelectedCompany] = useState<ApiCompany | null>(null);
  const companiesQuery = useQuery({
    queryKey: ['companies', 'directory', search, sector],
    queryFn: () => fetchAllCompanies(search, sector),
  });
  const marketQuery = useQuery({
    queryKey: ['market-analysis', '30d'],
    queryFn: () => fetchMarketAnalysis('30d'),
    refetchInterval: 5 * 60 * 1000,
  });
  const selectedCompanyQuery = useQuery({
    queryKey: ['company-selection', selectedCompanyId],
    queryFn: () => fetchCompanies({ search: selectedCompanyId || undefined }),
    enabled: Boolean(selectedCompanyId),
  });

  useEffect(() => {
    if (!selectedCompanyId || !selectedCompanyQuery.data) return;
    const company = selectedCompanyQuery.data.results.find(
      (item) =>
        item.symbol.toLowerCase() === selectedCompanyId.toLowerCase() ||
        String(item.id) === selectedCompanyId,
    );
    if (company) setSelectedCompany(company);
    setSelectedCompanyId(null);
  }, [selectedCompanyId, selectedCompanyQuery.data, setSelectedCompanyId]);

  const columns: Column<ApiCompany>[] = [
    {
      key: 'symbol',
      header: 'Symbol',
      sortable: true,
      render: (company) => (
        <div>
          <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
            {company.symbol}
          </span>
          <span className="block text-[11px] text-slate-500">{company.name}</span>
        </div>
      ),
    },
    { key: 'sector', header: 'Sector', sortable: true },
    {
      key: 'is_active',
      header: 'Status',
      render: (company) => (
        <span className={company.is_active ? 'text-emerald-600' : 'text-slate-500'}>
          {company.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Data',
      render: (company) => (
        <button
          onClick={() => setSelectedCompany(company)}
          className="rounded border border-slate-300 px-2.5 py-1 text-[11px] dark:border-slate-700"
        >
          Prices & analytics
        </button>
      ),
    },
  ];

  const companies = companiesQuery.data ?? [];
  const leaders = marketQuery.data?.snapshot;
  const topGainers = leaders?.top_gainers.slice(0, 10) ?? [];
  const topLosers = leaders?.top_losers.slice(0, 10) ?? [];
  const topTraded = leaders?.top_traded.slice(0, 10) ?? [];
  const companyBySymbol = new Map(
    companies.map((company) => [company.symbol.toUpperCase(), company]),
  );
  const leaderSymbols = new Set(
    [...topGainers, ...topLosers, ...topTraded].map((leader) =>
      leader.symbol.toUpperCase(),
    ),
  );
  const otherCompanies = companies.filter(
    (company) => !leaderSymbols.has(company.symbol.toUpperCase()),
  );
  const matchesFilters = (symbol: string, name: string) => {
    const company = companyBySymbol.get(symbol.toUpperCase());
    const matchesSearch =
      !search ||
      symbol.toLowerCase().includes(search.toLowerCase()) ||
      name.toLowerCase().includes(search.toLowerCase());
    return (
      matchesSearch &&
      (!sector || company?.sector.toLowerCase().includes(sector.toLowerCase()))
    );
  };
  const filteredGainers = topGainers.filter((leader) =>
    matchesFilters(leader.symbol, leader.name),
  );
  const filteredLosers = topLosers.filter((leader) =>
    matchesFilters(leader.symbol, leader.name),
  );
  const filteredTraded = topTraded.filter((leader) =>
    matchesFilters(leader.symbol, leader.name),
  );
  const filteredOthers = otherCompanies.filter((company) =>
    matchesFilters(company.symbol, company.name),
  );

  return (
    <div className="space-y-5">
      <PageHeader
        title="NEPSE Companies"
        description="Browse the top 10 daily gainers, losers, and traded companies, plus all remaining companies in Others."
        icon={Building2}
        badge={
          companiesQuery.data && (
            <span className="rounded-full bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">
              {companies.length} companies
            </span>
          )
        }
      />
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-[#111827] sm:flex-row">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search company or symbol"
          className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
        />
        <input
          value={sector}
          onChange={(event) => setSector(event.target.value)}
          placeholder="Filter by sector"
          className="rounded-lg border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
        />
      </div>

      {companiesQuery.isLoading ? (
        <LoadingState message="Loading companies…" />
      ) : companiesQuery.isError ? (
        <p role="alert" className="rounded-lg bg-rose-50 p-4 text-sm text-rose-700">
          {companiesQuery.error.message}
        </p>
      ) : companies.length ? (
        <div className="space-y-6">
          {marketQuery.isError && (
            <p role="alert" className="rounded-lg bg-rose-50 p-4 text-sm text-rose-700">
              {marketQuery.error.message}
            </p>
          )}
          {marketQuery.isLoading ? (
            <LoadingState message="Loading market leaders…" />
          ) : leaders ? (
            <>
              <LeaderSection
                title="Top 10 Gainers"
                leaders={filteredGainers}
                valueLabel="Change"
                companies={companyBySymbol}
                onSelectCompany={setSelectedCompany}
              />
              <LeaderSection
                title="Top 10 Losers"
                leaders={filteredLosers}
                valueLabel="Change"
                companies={companyBySymbol}
                onSelectCompany={setSelectedCompany}
              />
              <LeaderSection
                title="Top 10 Traded"
                leaders={filteredTraded}
                valueLabel="Turnover (Cr)"
                companies={companyBySymbol}
                onSelectCompany={setSelectedCompany}
              />
            </>
          ) : (
            <p className="rounded-lg border border-slate-200 p-4 text-sm text-slate-500 dark:border-slate-800">
              Market leader data is not available yet.
            </p>
          )}
          <section className="space-y-2">
            <h2 className="font-semibold">
              Others{' '}
              <span className="text-sm font-normal text-slate-500">
                ({filteredOthers.length})
              </span>
            </h2>
            <DataTable
              columns={columns}
              data={filteredOthers}
              keyExtractor={(company) => company.id}
              pageSize={25}
              emptyMessage="No other companies match the selected filters."
            />
          </section>
        </div>
      ) : (
        <EmptyState title="No companies found" description="No company records are available." />
      )}

      {selectedCompany && (
        <CompanyMarketData
          company={selectedCompany}
          onClose={() => {
            setSelectedCompany(null);
            setSelectedCompanyId(null);
          }}
        />
      )}
    </div>
  );
};

async function fetchAllCompanies(search: string, sector: string) {
  const params = {
    search: search || undefined,
    sector: sector || undefined,
  };
  const firstPage = await fetchCompanies({ ...params, page: 1 });
  const companies = [...firstPage.results];

  for (let page = 2; firstPage.next && companies.length < firstPage.count; page += 1) {
    const nextPage = await fetchCompanies({ ...params, page });
    companies.push(...nextPage.results);
    if (!nextPage.next) break;
  }

  return companies;
}

function LeaderSection({
  title,
  leaders,
  valueLabel,
  companies,
  onSelectCompany,
}: {
  title: string;
  leaders: ApiMarketLeader[];
  valueLabel: 'Change' | 'Turnover (Cr)';
  companies: Map<string, ApiCompany>;
  onSelectCompany: (company: ApiCompany) => void;
}) {
  const columns: Column<ApiMarketLeader>[] = [
    {
      key: 'symbol',
      header: 'Company',
      render: (leader) => (
        <div>
          <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
            {leader.symbol}
          </span>
          <span className="block text-[11px] text-slate-500">{leader.name}</span>
        </div>
      ),
    },
    {
      key: 'value',
      header: valueLabel,
      render: (leader) => {
        const value =
          valueLabel === 'Change' ? leader.change_percent : leader.turnover_crore;
        if (value === null || value === undefined) return 'Unavailable';
        return `${value}${valueLabel === 'Change' ? '%' : ''}`;
      },
    },
    {
      key: 'actions',
      header: 'Data',
      render: (leader) => {
        const company = companies.get(leader.symbol.toUpperCase());
        return company ? (
          <button
            onClick={() => onSelectCompany(company)}
            className="rounded border border-slate-300 px-2.5 py-1 text-[11px] dark:border-slate-700"
          >
            Prices & analytics
          </button>
        ) : (
          <span className="text-slate-400">Not in directory</span>
        );
      },
    },
  ];

  return (
    <section className="space-y-2">
      <h2 className="font-semibold">
        {title} <span className="text-sm font-normal text-slate-500">({leaders.length})</span>
      </h2>
      <DataTable
        columns={columns}
        data={leaders}
        keyExtractor={(leader) => leader.symbol}
        emptyMessage="No market leaders match the selected filters."
      />
    </section>
  );
}

function CompanyMarketData({
  company,
  onClose,
}: {
  company: ApiCompany;
  onClose: () => void;
}) {
  const [range, setRange] = useState<ApiMarketHistoryRange>('30d');
  const pricesQuery = useQuery({
    queryKey: ['company-prices', company.id, range],
    queryFn: () => fetchCompanyPrices(company.id, range),
  });
  const behaviorQuery = useQuery({
    queryKey: ['company-behavior', company.id, range],
    queryFn: () => fetchCompanyBehaviorSummary(company.id, range),
  });
  const floorsheetQuery = useQuery({
    queryKey: ['company-floorsheet', company.id],
    queryFn: () => fetchCompanyFloorsheet(company.id),
  });
  const behavior = behaviorQuery.data;
  const prices = pricesQuery.data ?? [];
  const history = [...prices].sort((first, second) => first.date.localeCompare(second.date));
  const chartData = history.map((price) => ({
    date: price.date,
    close: Number(price.close_price),
  }));
  const lastUpdated = prices.reduce(
    (latest, price) => (price.updated_at > latest ? price.updated_at : latest),
    '',
  );
  const formattedLastUpdated = lastUpdated
    ? new Intl.DateTimeFormat('en-NP', {
        timeZone: 'Asia/Kathmandu',
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(lastUpdated))
    : 'Unavailable';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <section className="max-h-[90vh] w-full max-w-4xl space-y-4 overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-[#111827]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">
              {company.symbol} · {company.name}
            </h2>
            <p className="text-sm text-slate-500">{company.sector || 'Sector unavailable'}</p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={range}
              onChange={(event) => setRange(event.target.value as ApiMarketHistoryRange)}
              className="rounded border border-slate-300 bg-transparent px-2 py-1 text-sm dark:border-slate-700"
              aria-label="Price date range"
            >
              <option value="7d">7 days</option>
              <option value="15d">15 days</option>
              <option value="30d">30 days</option>
              <option value="90d">90 days</option>
              <option value="180d">180 days</option>
              <option value="1y">1 year</option>
              <option value="all">All available</option>
            </select>
            <button onClick={onClose} className="text-sm text-slate-500">
              Close
            </button>
          </div>
        </div>

        {behaviorQuery.isLoading ? (
          <LoadingState message="Loading market analysis…" />
        ) : behaviorQuery.isError ? (
          <p role="alert" className="text-sm text-rose-600">
            {behaviorQuery.error.message}
          </p>
        ) : behavior ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Latest close" value={behavior.latest_price?.close ?? 'Unavailable'} />
            <Metric
              label="Price change"
              value={
                behavior.price_change_percent === null
                  ? 'Unavailable'
                  : `${behavior.price_change_percent}%`
              }
            />
            <Metric
              label="Floorsheet VWAP"
              value={behavior.vwap.available ? behavior.vwap.value ?? 'Unavailable' : 'Unavailable'}
              detail={behavior.vwap.limitation ?? 'Calculated from transaction-level floorsheet data.'}
            />
            <Metric
              label="Close-location indicator"
              value={
                behavior.latest_pressure_indicator.available
                  ? behavior.latest_pressure_indicator.score ?? 'Unavailable'
                  : 'Unavailable'
              }
              detail={behavior.latest_pressure_indicator.interpretation}
            />
            <Metric
              label="20-day volume anomaly"
              value={
                behavior.latest_volume_anomaly.available
                  ? behavior.latest_volume_anomaly.is_anomaly
                    ? 'Detected'
                    : 'Not detected'
                  : 'Unavailable'
              }
              detail={behavior.latest_volume_anomaly.reason}
            />
            <Metric
              label="Floorsheet records"
              value={
                behavior.floorsheet.available
                  ? `${behavior.floorsheet.transactions} transactions`
                  : 'Unavailable'
              }
              detail={behavior.floorsheet.brokers.limitation}
            />
          </div>
        ) : null}

        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h3 className="font-semibold">Historical OHLCV</h3>
            <p className="text-xs text-slate-500">
              Available data: {history[0]?.date ?? 'Unavailable'} –{' '}
              {history[history.length - 1]?.date ?? 'Unavailable'}
            </p>
          </div>
          <p className="text-xs text-slate-500">Updated {formattedLastUpdated} NPT</p>
        </div>
        {pricesQuery.isLoading ? (
          <LoadingState message="Loading recorded prices…" />
        ) : pricesQuery.isError ? (
          <p role="alert" className="text-sm text-rose-600">
            {pricesQuery.error.message}
          </p>
        ) : history.length ? (
          <>
            <div className="h-56 w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.45} />
                  <XAxis dataKey="date" minTickGap={28} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis domain={['auto', 'auto']} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#111827',
                      borderColor: '#334155',
                      color: '#e2e8f0',
                    }}
                    formatter={(value) => [String(value), 'Close']}
                    labelFormatter={(value) => String(value)}
                  />
                  <Area
                    type="monotone"
                    dataKey="close"
                    name="Close"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.15}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    {['Date', 'Open', 'High', 'Low', 'Close', 'Change %', 'Volume', 'Source'].map(
                      (heading) => (
                        <th key={heading} className="px-2 py-2">
                          {heading}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {[...history].reverse().map((price) => (
                    <tr key={price.id} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="px-2 py-2">{price.date}</td>
                      <td className="px-2 py-2">{price.open_price}</td>
                      <td className="px-2 py-2">{price.high_price}</td>
                      <td className="px-2 py-2">{price.low_price}</td>
                      <td className="px-2 py-2">{price.close_price}</td>
                      <td className="px-2 py-2">
                        {price.change_percent === null
                          ? 'Unavailable'
                          : `${price.change_percent}%`}
                      </td>
                      <td className="px-2 py-2">{price.volume.toLocaleString()}</td>
                      <td className="px-2 py-2">{price.source || 'Not recorded'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <EmptyState
            title="No recorded prices"
            description="No OHLCV records are available for this company and date range. No values are estimated or substituted."
          />
        )}

        <div>
          <h3 className="font-semibold">Floorsheet transactions</h3>
          {floorsheetQuery.isLoading ? (
            <LoadingState message="Loading recorded transactions…" />
          ) : floorsheetQuery.isError ? (
            <p role="alert" className="text-sm text-rose-600">
              {floorsheetQuery.error.message}
            </p>
          ) : floorsheetQuery.data?.length ? (
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    {['Date', 'Contract', 'Buyer', 'Seller', 'Rate', 'Quantity', 'Source'].map(
                      (heading) => (
                        <th key={heading} className="px-2 py-2">{heading}</th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {floorsheetQuery.data.map((trade) => (
                    <tr key={trade.id} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="px-2 py-2">{trade.trade_date}</td>
                      <td className="px-2 py-2 font-mono">{trade.transaction_id || 'Unavailable'}</td>
                      <td className="px-2 py-2">{trade.buyer_broker || 'Unavailable'}</td>
                      <td className="px-2 py-2">{trade.seller_broker || 'Unavailable'}</td>
                      <td className="px-2 py-2">{trade.price}</td>
                      <td className="px-2 py-2">{trade.quantity.toLocaleString()}</td>
                      <td className="px-2 py-2">{trade.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No recorded floorsheet trades"
              description="No transaction-level records are available for this company."
            />
          )}
        </div>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string | null;
}) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 font-mono font-semibold">{value}</p>
      {detail && <p className="mt-1 text-[11px] text-slate-500">{detail}</p>}
    </div>
  );
}
