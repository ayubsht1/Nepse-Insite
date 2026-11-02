'use client';

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ApiCompany, fetchCompanies, fetchCompanyBehaviorSummary, fetchCompanyPrices } from '../../services/api';
import { useApp } from '../../context/AppContext';
import { DataTable, EmptyState, LoadingState, PageHeader } from '../../components/ui';
import { Column } from '../../components/ui/DataTable';
import { Building2 } from 'lucide-react';

export const CompaniesView: React.FC = () => {
  const { selectedCompanyId, setSelectedCompanyId } = useApp();
  const [search, setSearch] = useState('');
  const [sector, setSector] = useState('');
  const [page, setPage] = useState(1);
  const [selectedCompany, setSelectedCompany] = useState<ApiCompany | null>(null);
  const companiesQuery = useQuery({
    queryKey: ['companies', search, sector, page],
    queryFn: () =>
      fetchCompanies({
        search: search || undefined,
        sector: sector || undefined,
        page,
      }),
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

  const result = companiesQuery.data;
  const pageCount = result ? Math.max(1, Math.ceil(result.count / 25)) : 1;

  return (
    <div className="space-y-5">
      <PageHeader
        title="NEPSE Companies"
        description="Company records and trading data returned by the backend. Prices and analytics remain unavailable until verified records are imported."
        icon={Building2}
        badge={
          result && (
            <span className="rounded-full bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">
              {result.count} companies
            </span>
          )
        }
      />
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-[#111827] sm:flex-row">
        <input
          type="search"
          value={search}
          onChange={(event) => {
            setPage(1);
            setSearch(event.target.value);
          }}
          placeholder="Search company or symbol"
          className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
        />
        <input
          value={sector}
          onChange={(event) => {
            setPage(1);
            setSector(event.target.value);
          }}
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
      ) : result?.results.length ? (
        <>
          <DataTable
            columns={columns}
            data={result.results}
            keyExtractor={(company) => company.id}
          />
          {pageCount > 1 && (
            <div className="flex items-center justify-end gap-3 text-sm">
              <button
                disabled={page <= 1}
                onClick={() => setPage((current) => current - 1)}
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40 dark:border-slate-700"
              >
                Previous
              </button>
              <span>
                Page {page} of {pageCount}
              </span>
              <button
                disabled={page >= pageCount}
                onClick={() => setPage((current) => current + 1)}
                className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40 dark:border-slate-700"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        <EmptyState
          title="No companies found"
          description="The company directory is empty or no records match the selected filters."
        />
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

function CompanyMarketData({
  company,
  onClose,
}: {
  company: ApiCompany;
  onClose: () => void;
}) {
  const [range, setRange] = useState<'7d' | '15d' | '30d'>('30d');
  const pricesQuery = useQuery({
    queryKey: ['company-prices', company.id, range],
    queryFn: () => fetchCompanyPrices(company.id, range),
  });
  const behaviorQuery = useQuery({
    queryKey: ['company-behavior', company.id, range],
    queryFn: () => fetchCompanyBehaviorSummary(company.id, range),
  });
  const behavior = behaviorQuery.data;

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
              onChange={(event) =>
                setRange(event.target.value as '7d' | '15d' | '30d')
              }
              className="rounded border border-slate-300 bg-transparent px-2 py-1 text-sm dark:border-slate-700"
              aria-label="Price date range"
            >
              <option value="7d">7 days</option>
              <option value="15d">15 days</option>
              <option value="30d">30 days</option>
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

        <h3 className="font-semibold">Historical OHLCV</h3>
        {pricesQuery.isLoading ? (
          <LoadingState message="Loading recorded prices…" />
        ) : pricesQuery.isError ? (
          <p role="alert" className="text-sm text-rose-600">
            {pricesQuery.error.message}
          </p>
        ) : pricesQuery.data?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  {['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Source'].map(
                    (heading) => (
                      <th key={heading} className="px-2 py-2">
                        {heading}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {pricesQuery.data.map((price) => (
                  <tr key={price.id} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="px-2 py-2">{price.date}</td>
                    <td className="px-2 py-2">{price.open_price}</td>
                    <td className="px-2 py-2">{price.high_price}</td>
                    <td className="px-2 py-2">{price.low_price}</td>
                    <td className="px-2 py-2">{price.close_price}</td>
                    <td className="px-2 py-2">{price.volume.toLocaleString()}</td>
                    <td className="px-2 py-2">{price.source || 'Not recorded'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No recorded prices"
            description="No OHLCV records are available for this company and date range. No values are estimated or substituted."
          />
        )}
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
