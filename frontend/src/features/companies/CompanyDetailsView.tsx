import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { getCompanyDetails } from '../../data/companyDetailsData';
import { formatNPR, formatPercent, formatVolume, formatLargeAmount } from '../../lib/utils';
import {
  PageHeader,
  StatCard,
  ChartCard,
  StatusBadge,
  DataTable,
  Column,
  LoadingState,
  EmptyState,
} from '../../components/ui';
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Building2,
  Newspaper,
  Layers,
  Activity,
  AlertTriangle,
  Info,
  Calendar,
  ExternalLink,
  ShieldAlert,
  SlidersHorizontal,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Line,
} from 'recharts';
import { BrokerTradeSummary, CompanyHistoricalOHLCV } from '../../types';

interface CompanyDetailsViewProps {
  onBack: () => void;
}

export const CompanyDetailsView: React.FC<CompanyDetailsViewProps> = ({ onBack }) => {
  const { selectedCompanyId } = useApp();
  const [timeframe, setTimeframe] = useState<'7D' | '15D' | '30D'>('30D');
  const [uiState, setUiState] = useState<'normal' | 'loading' | 'empty'>('normal');

  const company = getCompanyDetails(selectedCompanyId || 'nabil');
  const historyData = company.historicalData[timeframe] || company.historicalData['30D'];

  const isPositive = company.change >= 0;
  const vwapDiff = company.price - company.vwap;
  const vwapDiffPercent = (vwapDiff / company.vwap) * 100;

  // Custom Tooltip for Price & VWAP Area Chart
  const CustomPriceTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data: CompanyHistoricalOHLCV = payload[0].payload;
      const isDayPositive = data.close >= data.open;
      return (
        <div className="p-3 bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-700/80 rounded-lg shadow-xl text-xs space-y-1.5 min-w-[200px]">
          <div className="font-semibold text-slate-700 dark:text-slate-300 pb-1 border-b border-slate-200 dark:border-slate-800 flex justify-between">
            <span>{data.date}</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">
              {formatNPR(data.close)}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-[11px] text-slate-500 dark:text-slate-400">
            <div>Open: <span className="text-slate-800 dark:text-slate-200">{formatNPR(data.open)}</span></div>
            <div>Close: <span className={isDayPositive ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-rose-600 dark:text-rose-400 font-semibold'}>{formatNPR(data.close)}</span></div>
            <div>High: <span className="text-slate-800 dark:text-slate-200">{formatNPR(data.high)}</span></div>
            <div>Low: <span className="text-slate-800 dark:text-slate-200">{formatNPR(data.low)}</span></div>
          </div>
          <div className="pt-1 border-t border-slate-200 dark:border-slate-800/80 text-[11px] flex justify-between font-mono">
            <span className="text-slate-500 dark:text-slate-500">Indicative VWAP:</span>
            <span className="text-sky-600 dark:text-sky-400 font-semibold">{formatNPR(data.vwap)}</span>
          </div>
          <div className="text-[11px] flex justify-between font-mono">
            <span className="text-slate-500 dark:text-slate-500">Volume:</span>
            <span className="text-slate-800 dark:text-slate-200">{formatVolume(data.volume)} shares</span>
          </div>
        </div>
      );
    }
    return null;
  };

  // Custom Tooltip for Volume Bar Chart
  const CustomVolumeTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data: CompanyHistoricalOHLCV = payload[0].payload;
      return (
        <div className="p-2.5 bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-700/80 rounded-lg shadow-xl text-xs font-mono space-y-1">
          <div className="text-slate-700 dark:text-slate-300">{data.date}</div>
          <div className="text-slate-500 dark:text-slate-400 flex justify-between gap-4">
            <span>Session Volume:</span>
            <span className="text-sky-600 dark:text-sky-400 font-bold">{formatVolume(data.volume)}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  // Broker Breakdown Table Columns
  const brokerColumns: Column<BrokerTradeSummary>[] = [
    {
      key: 'brokerNumber',
      header: 'Broker',
      sortable: true,
      render: (b) => (
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-xs px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200">
            #{b.brokerNumber}
          </span>
          <span className="text-xs text-slate-700 dark:text-slate-300 truncate max-w-[160px]">
            {b.brokerName}
          </span>
        </div>
      ),
    },
    {
      key: 'buyVolume',
      header: 'Bought Shares',
      align: 'right',
      sortable: true,
      render: (b) => (
        <span className="font-mono text-emerald-400 font-medium">
          {b.buyVolume.toLocaleString('en-IN')}
        </span>
      ),
    },
    {
      key: 'sellVolume',
      header: 'Sold Shares',
      align: 'right',
      sortable: true,
      render: (b) => (
        <span className="font-mono text-rose-400 font-medium">
          {b.sellVolume.toLocaleString('en-IN')}
        </span>
      ),
    },
    {
      key: 'netShares',
      header: 'Net Position',
      align: 'right',
      sortable: true,
      render: (b) => {
        const isNetBuyer = b.netShares >= 0;
        return (
          <span
            className={`font-mono font-bold tabular-nums ${
              isNetBuyer ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {isNetBuyer ? `+${b.netShares.toLocaleString('en-IN')}` : b.netShares.toLocaleString('en-IN')}
          </span>
        );
      },
    },
    {
      key: 'netAmount',
      header: 'Net Value (NPR)',
      align: 'right',
      sortable: true,
      render: (b) => (
        <span className="font-mono text-slate-700 dark:text-slate-300">
          {formatNPR(Math.abs(b.netAmount), false)}
        </span>
      ),
    },
  ];

  if (uiState === 'loading') {
    return (
      <div className="space-y-6">
        <button
          onClick={() => setUiState('normal')}
          className="text-xs px-3 py-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded border border-slate-200 dark:border-slate-700"
        >
          Exit Loading State
        </button>
        <LoadingState variant="skeleton-cards" count={4} />
        <LoadingState variant="skeleton-table" count={6} />
      </div>
    );
  }

  if (uiState === 'empty') {
    return (
      <div className="space-y-6">
        <button
          onClick={() => setUiState('normal')}
          className="text-xs px-3 py-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded border border-slate-200 dark:border-slate-700 mb-4"
        >
          Reset View
        </button>
        <EmptyState
          title="Company Analytics Unavailable"
          description={`Floorsheet and trade ticks for ${company.symbol} are currently unrecorded or pending end-of-day reconciliation.`}
          actionLabel="Return to Companies Directory"
          onAction={onBack}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Navigation & Breadcrumb Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800/80 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white border border-slate-200 dark:border-transparent transition-colors shadow-2xs"
            title="Back to Companies Directory"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold font-mono text-slate-900 dark:text-white tracking-tight">
                {company.symbol}
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400 font-sans">
                {company.name}
              </span>
              <StatusBadge label={company.sector} variant="info" />
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              <span>Exchange: NEPSE</span>
              <span>·</span>
              <span>ISIN: NPL{company.symbol}000</span>
              <span>·</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-mono">Real-time Tick Data</span>
            </div>
          </div>
        </div>

        {/* Price Lockup */}
        <div className="flex items-baseline gap-3 self-end sm:self-auto text-right">
          <div>
            <div className="text-2xl font-bold font-mono text-slate-900 dark:text-white">
              {formatNPR(company.price)}
            </div>
            <div
              className={`flex items-center justify-end gap-1 font-mono text-xs font-semibold ${
                isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
              }`}
            >
              {isPositive ? <TrendingUp className="w-3.5 h-3.5 inline" /> : <TrendingDown className="w-3.5 h-3.5 inline" />}
              <span>{company.change > 0 ? `+${company.change}` : company.change}</span>
              <span>({formatPercent(company.changePercent)})</span>
            </div>
          </div>
        </div>
      </div>

      {/* 52-Week Range Bar */}
      <div className="p-3.5 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 text-xs shadow-xs">
        <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 mb-2 font-mono">
          <span>52-Week Low: <strong className="text-slate-800 dark:text-slate-200">{formatNPR(company.week52Low)}</strong></span>
          <span className="font-sans text-[11px] text-slate-400 dark:text-slate-500">Yearly Price Range</span>
          <span>52-Week High: <strong className="text-slate-800 dark:text-slate-200">{formatNPR(company.week52High)}</strong></span>
        </div>
        <div className="w-full h-2 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden relative">
          <div
            className="h-full bg-gradient-to-r from-rose-500 via-amber-400 to-emerald-500 rounded-full"
            style={{ width: '100%' }}
          />
        </div>
        <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono mt-1">
          <span>Current Position: {Math.round(((company.price - company.week52Low) / (company.week52High - company.week52Low)) * 100)}% of 52W range</span>
          <span className="text-slate-500 dark:text-slate-400">Beta: {company.volatility}</span>
        </div>
      </div>

      {/* OHLC and Financial Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3 rounded-lg bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-0.5">Open</span>
          <span className="font-mono font-bold text-sm text-slate-900 dark:text-slate-100">{formatNPR(company.open)}</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-0.5">Day High</span>
          <span className="font-mono font-bold text-sm text-emerald-600 dark:text-emerald-400">{formatNPR(company.high)}</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-0.5">Day Low</span>
          <span className="font-mono font-bold text-sm text-rose-600 dark:text-rose-400">{formatNPR(company.low)}</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-0.5">Close (LTP)</span>
          <span className="font-mono font-bold text-sm text-slate-900 dark:text-slate-100">{formatNPR(company.price)}</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-0.5">Day Volume</span>
          <span className="font-mono font-bold text-sm text-slate-900 dark:text-slate-100">{formatVolume(company.volume)} shs</span>
        </div>
        <div className="p-3 rounded-lg bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-2xs">
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block mb-0.5">Day Turnover</span>
          <span className="font-mono font-bold text-sm text-emerald-600 dark:text-emerald-400">{formatNPR(company.turnover, false)}</span>
        </div>
      </div>

      {/* Advanced Indicators Strip: P/E, EPS, Market Cap, Indicative VWAP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Indicative VWAP */}
        <div className="p-4 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span className="font-medium">Indicative VWAP</span>
            <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">Floorsheet Est.</span>
          </div>
          <div className="text-xl font-bold font-mono text-slate-900 dark:text-white">
            {formatNPR(company.vwap)}
          </div>
          <div className="mt-2 text-[11px] flex items-center justify-between font-mono">
            <span className="text-slate-500 dark:text-slate-400">Delta vs LTP:</span>
            <span className={vwapDiff >= 0 ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-rose-600 dark:text-rose-400 font-semibold'}>
              {vwapDiff >= 0 ? `+${vwapDiff.toFixed(1)} (+${vwapDiffPercent.toFixed(2)}%)` : `${vwapDiff.toFixed(1)} (${vwapDiffPercent.toFixed(2)}%)`}
            </span>
          </div>
        </div>

        {/* Metric 2: P/E Ratio (with unavailable handling) */}
        <div className="p-4 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span className="font-medium">P/E Ratio (TTM)</span>
            <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">Sector: ~18.5</span>
          </div>
          <div className="text-xl font-bold font-mono text-slate-900 dark:text-white">
            {company.peRatio ? `${company.peRatio.toFixed(1)}x` : <span className="text-slate-400 dark:text-slate-500 text-sm">Unavailable</span>}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between font-mono">
            <span>EPS (TTM):</span>
            <span className="text-slate-800 dark:text-slate-200">
              {company.eps !== undefined ? `Rs. ${company.eps.toFixed(2)}` : <span className="text-slate-400 dark:text-slate-500 font-normal">N/A</span>}
            </span>
          </div>
        </div>

        {/* Metric 3: Market Capitalization */}
        <div className="p-4 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span className="font-medium">Market Capitalization</span>
            <Building2 className="w-3.5 h-3.5 text-sky-500 dark:text-sky-400" />
          </div>
          <div className="text-xl font-bold font-mono text-slate-900 dark:text-white">
            {company.marketCap ? formatLargeAmount(company.marketCap) : 'Rs. --'}
          </div>
          <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between font-mono">
            <span>Book Value:</span>
            <span className="text-slate-800 dark:text-slate-200">Rs. {company.bookValue}</span>
          </div>
        </div>

        {/* Metric 4: Volume Anomaly Indicator */}
        <div className={`p-4 rounded-xl border shadow-xs ${
          company.anomalyInfo.isAnomaly
            ? 'bg-purple-50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800/80'
            : 'bg-white dark:bg-[#111827] border-slate-200 dark:border-slate-800'
        }`}>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="font-medium text-slate-700 dark:text-slate-300">Volume Anomaly Radar</span>
            {company.anomalyInfo.isAnomaly ? (
              <span className="text-[10px] font-mono font-bold text-purple-700 dark:text-purple-400 bg-purple-100 dark:bg-purple-950/60 border border-purple-300 dark:border-purple-800/60 px-1.5 py-0.5 rounded">
                FLAGGED
              </span>
            ) : (
              <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">Normal</span>
            )}
          </div>
          <div className="text-xl font-bold font-mono text-slate-900 dark:text-white">
            {company.anomalyInfo.anomalyScore}x <span className="text-xs font-normal text-slate-500 dark:text-slate-400">vs 20D Avg</span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 truncate" title={company.anomalyInfo.interpretation}>
            {company.anomalyInfo.isAnomaly ? 'Elevated order velocity' : 'Within normal trading band'}
          </div>
        </div>
      </div>

      {/* Historical Charts: OHLCV Price & VWAP Area Chart + Synchronized Volume */}
      <div className="grid grid-cols-1 gap-6">
        {/* Chart 1: Price and VWAP */}
        <ChartCard
          title={`${company.symbol} Historical Price & Indicative VWAP`}
          subtitle="Closing price trajectory compared against Volume Weighted Average Price (VWAP)"
          timeframeOptions={['7D', '15D', '30D']}
          selectedTimeframe={timeframe}
          onTimeframeChange={(tf) => setTimeframe(tf as any)}
          footer={
            <div className="flex flex-wrap items-center justify-between gap-3 text-slate-400">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />
                  <span>Closing Price</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-0.5 bg-sky-400" />
                  <span>Indicative VWAP</span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500">
                *Note: VWAP represents floorsheet executed transaction volume weighted average price.
              </div>
            </div>
          }
        >
          <div className="h-64 sm:h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={historyData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                <defs>
                  <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="var(--chart-axis)"
                  tick={{ fill: 'var(--chart-label)' }}
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--chart-axis)' }}
                />
                <YAxis
                  stroke="var(--chart-axis)"
                  tick={{ fill: 'var(--chart-label)' }}
                  fontSize={11}
                  domain={['dataMin - 10', 'dataMax + 10']}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--chart-axis)' }}
                  tickFormatter={(val) => Math.round(val).toString()}
                />
                <Tooltip content={<CustomPriceTooltip />} />
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#priceGradient)"
                />
                <Line
                  type="monotone"
                  dataKey="vwap"
                  stroke="#38bdf8"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        {/* Chart 2: Synchronized Volume Bar Chart */}
        <ChartCard
          title="Daily Share Volume"
          subtitle="Volume of shares traded per session (with 20-day moving average reference)"
          footer={
            <div className="flex items-center justify-between text-slate-400 text-[11px]">
              <span>Average 20D Volume: {formatVolume(company.anomalyInfo.avgVolume20D)} shares</span>
              <span className="font-mono text-sky-400">Latest Session: {formatVolume(company.volume)} shares</span>
            </div>
          }
        >
          <div className="h-32 sm:h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={historyData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="var(--chart-axis)"
                  tick={{ fill: 'var(--chart-label)' }}
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--chart-axis)' }}
                />
                <YAxis
                  stroke="var(--chart-axis)"
                  tick={{ fill: 'var(--chart-label)' }}
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--chart-axis)' }}
                  tickFormatter={(v) => formatVolume(v)}
                />
                <Tooltip content={<CustomVolumeTooltip />} />
                <ReferenceLine
                  y={company.anomalyInfo.avgVolume20D}
                  stroke="#f59e0b"
                  strokeDasharray="3 3"
                  label={{ value: '20D Avg', fill: '#f59e0b', fontSize: 10, position: 'insideTopRight' }}
                />
                <Bar dataKey="volume" fill="#0284c7" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      </div>

      {/* Advanced Order-Flow Intelligence: Buy/Sell Pressure & Broker Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Estimated Buy/Sell Pressure Card */}
        <div className="p-5 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Estimated Buy/Sell Pressure
              </h3>
            </div>
            <StatusBadge
              label={company.pressureInfo.status}
              variant={company.pressureInfo.buyPercent >= 55 ? 'success' : 'warning'}
            />
          </div>

          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            Derived from tick-level execution aggression (trades executing at Ask versus Bid). Labeled strictly as an estimate.
          </p>

          {/* Segmented Pressure Bar */}
          <div className="space-y-1.5 pt-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                {company.pressureInfo.buyPercent}% Buying Pressure
              </span>
              <span className="text-rose-600 dark:text-rose-400 font-bold">
                {company.pressureInfo.sellPercent}% Selling Pressure
              </span>
            </div>
            <div className="h-3 w-full bg-slate-200 dark:bg-slate-800 rounded-full flex overflow-hidden p-0.5 border border-slate-300 dark:border-slate-700/80">
              <div
                className="h-full bg-emerald-500 rounded-l-full transition-all duration-300"
                style={{ width: `${company.pressureInfo.buyPercent}%` }}
              />
              <div
                className="h-full bg-rose-500 rounded-r-full transition-all duration-300"
                style={{ width: `${company.pressureInfo.sellPercent}%` }}
              />
            </div>
          </div>

          <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 text-[11px] font-mono space-y-1">
            <div className="flex justify-between text-slate-500 dark:text-slate-400">
              <span>Estimated Buy Volume:</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">{company.pressureInfo.buyVolume.toLocaleString('en-IN')} shs</span>
            </div>
            <div className="flex justify-between text-slate-500 dark:text-slate-400">
              <span>Estimated Sell Volume:</span>
              <span className="text-rose-600 dark:text-rose-400 font-semibold">{company.pressureInfo.sellVolume.toLocaleString('en-IN')} shs</span>
            </div>
          </div>

          <div className="text-[10px] text-slate-500 dark:text-slate-500 flex items-start gap-1 leading-normal">
            <Info className="w-3 h-3 shrink-0 mt-0.5 text-slate-400" />
            <span>{company.pressureInfo.methodologyNote}</span>
          </div>
        </div>

        {/* Broker-Level Buying & Selling Breakdown Table */}
        <div className="lg:col-span-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] shadow-xs overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#151d30] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-sky-500 dark:text-sky-400" />
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Broker-Level Buying & Selling Breakdown
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Top institutional and retail brokers active in {company.symbol} today
                </p>
              </div>
            </div>
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
              6 Active Brokers Tracked
            </span>
          </div>

          <DataTable
            columns={brokerColumns}
            data={company.brokerBreakdown}
            keyExtractor={(b) => b.brokerNumber}
            className="border-0 rounded-none shadow-none"
          />

          <div className="p-3 bg-slate-50 dark:bg-[#0e1422] border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-600 dark:text-slate-400">
            <span>Top Accumulator: Broker 58 (Net +24,300 shs)</span>
            <span>Top Distributor: Broker 19 (Net -9,900 shs)</span>
          </div>
        </div>
      </div>

      {/* Related Financial News Feed for Selected Company */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#151d30] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Newspaper className="w-4 h-4 text-purple-500 dark:text-purple-400" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Related Financial News & Disclosures for {company.symbol}
            </h3>
          </div>
          <span className="text-xs text-purple-600 dark:text-purple-400 font-mono font-medium">
            {company.relatedNews.length} Tagged Articles
          </span>
        </div>

        <div className="divide-y divide-slate-100 dark:divide-slate-800/60 p-2">
          {company.relatedNews.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              No recent news articles tagged specifically for {company.symbol}.
            </div>
          ) : (
            company.relatedNews.map((item) => (
              <div
                key={item.id}
                className="p-3.5 hover:bg-slate-50 dark:hover:bg-slate-800/40 rounded-lg transition-colors flex flex-col md:flex-row md:items-start justify-between gap-3"
              >
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-mono text-[11px] font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-2 py-0.5 rounded">
                      {item.source}
                    </span>
                    <span className="text-slate-400 dark:text-slate-500">·</span>
                    <span className="text-slate-500 dark:text-slate-400 text-[11px] font-mono">{item.publishedAt}</span>
                    <span className="text-slate-400 dark:text-slate-500">·</span>
                    <span className="text-purple-600 dark:text-purple-400 font-mono text-[11px]">{item.category}</span>
                    <span className="text-slate-400 dark:text-slate-500">·</span>
                    <span className="text-emerald-600 dark:text-emerald-400 text-[10px] font-mono font-semibold">
                      {Math.round(item.confidence * 100)}% Confidence
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                    {item.headline}
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed line-clamp-2">
                    {item.excerpt}
                  </p>
                </div>
                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white flex items-center gap-1 shrink-0 self-end md:self-auto transition-colors"
                  >
                    <span>Source</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
