import { CompanyDetails, CompanyHistoricalOHLCV, BrokerTradeSummary, VolumeAnomalyInfo, BuySellPressureInfo } from '../types';
import { MOCK_COMPANIES, MOCK_NEWS_FEED } from './mockData';

// Generates realistic 30-day historical OHLCV data with slight variations around the base price
function generateHistoricalOHLCV(basePrice: number, volatility: number): {
  '7D': CompanyHistoricalOHLCV[];
  '15D': CompanyHistoricalOHLCV[];
  '30D': CompanyHistoricalOHLCV[];
} {
  const dates30D = [
    'Oct 02', 'Oct 03', 'Oct 04', 'Oct 05', 'Oct 08', 'Oct 09', 'Oct 10',
    'Oct 11', 'Oct 12', 'Oct 15', 'Oct 16', 'Oct 17', 'Oct 18', 'Oct 19',
    'Oct 22', 'Oct 23', 'Oct 24', 'Oct 25', 'Oct 26', 'Oct 29', 'Oct 30',
    'Oct 31', 'Nov 01', 'Nov 02', 'Nov 05', 'Nov 06', 'Nov 07', 'Nov 08',
    'Nov 09', 'Nov 12 (Today)'
  ];

  let currentClose = basePrice * 0.92;
  const all30Days: CompanyHistoricalOHLCV[] = [];

  for (let i = 0; i < dates30D.length; i++) {
    const dailyReturn = (Math.sin(i * 0.7) * 0.015 + (Math.cos(i * 1.2) * 0.02) * volatility);
    const open = Math.round(currentClose * (1 + (Math.random() - 0.5) * 0.005) * 10) / 10;
    const close = Math.round(open * (1 + dailyReturn) * 10) / 10;
    const high = Math.round(Math.max(open, close) * (1 + Math.abs(Math.sin(i)) * 0.012) * 10) / 10;
    const low = Math.round(Math.min(open, close) * (1 - Math.abs(Math.cos(i)) * 0.01) * 10) / 10;
    const volume = Math.round(120000 + Math.sin(i * 0.5) * 60000 + (i === dates30D.length - 1 ? 75000 : 0));
    const vwap = Math.round(((open + high + low + close) / 4 + (Math.random() - 0.5) * 1.5) * 10) / 10;

    all30Days.push({
      date: dates30D[i],
      open,
      high,
      low,
      close,
      volume,
      vwap,
    });

    currentClose = close;
  }

  // Ensure last entry matches basePrice
  if (all30Days.length > 0) {
    all30Days[all30Days.length - 1].close = basePrice;
  }

  return {
    '7D': all30Days.slice(-7),
    '15D': all30Days.slice(-15),
    '30D': all30Days,
  };
}

export function getCompanyDetails(companyId: string): CompanyDetails {
  const baseCompany = MOCK_COMPANIES.find((c) => c.id === companyId) || MOCK_COMPANIES[0];
  const history = generateHistoricalOHLCV(baseCompany.price, baseCompany.volatility || 1.2);

  // Broker trading breakdown data
  const brokerBreakdown: BrokerTradeSummary[] = [
    {
      brokerNumber: 58,
      brokerName: 'Online Securities Ltd.',
      buyVolume: 42500,
      buyAmount: 42500 * baseCompany.price,
      sellVolume: 18200,
      sellAmount: 18200 * baseCompany.price,
      netShares: 24300,
      netAmount: 24300 * baseCompany.price,
    },
    {
      brokerNumber: 45,
      brokerName: 'Imperial Securities Co.',
      buyVolume: 34800,
      buyAmount: 34800 * baseCompany.price,
      sellVolume: 12400,
      sellAmount: 12400 * baseCompany.price,
      netShares: 22400,
      netAmount: 22400 * baseCompany.price,
    },
    {
      brokerNumber: 34,
      brokerName: 'Vision Securities Pvt. Ltd.',
      buyVolume: 28900,
      buyAmount: 28900 * baseCompany.price,
      sellVolume: 31200,
      sellAmount: 31200 * baseCompany.price,
      netShares: -2300,
      netAmount: -2300 * baseCompany.price,
    },
    {
      brokerNumber: 28,
      brokerName: 'Shrikrishna Securities Ltd.',
      buyVolume: 19400,
      buyAmount: 19400 * baseCompany.price,
      sellVolume: 26800,
      sellAmount: 26800 * baseCompany.price,
      netShares: -7400,
      netAmount: -7400 * baseCompany.price,
    },
    {
      brokerNumber: 49,
      brokerName: 'Online Securities Broker 49',
      buyVolume: 26100,
      buyAmount: 26100 * baseCompany.price,
      sellVolume: 14500,
      sellAmount: 14500 * baseCompany.price,
      netShares: 11600,
      netAmount: 11600 * baseCompany.price,
    },
    {
      brokerNumber: 19,
      brokerName: 'Nepal Stock House Pvt. Ltd.',
      buyVolume: 14200,
      buyAmount: 14200 * baseCompany.price,
      sellVolume: 24100,
      sellAmount: 24100 * baseCompany.price,
      netShares: -9900,
      netAmount: -9900 * baseCompany.price,
    },
  ];

  // Volume anomaly calculation
  const avg20D = Math.round(baseCompany.volume * 0.42);
  const ratio = Math.round((baseCompany.volume / avg20D) * 10) / 10;
  const isAnomaly = ratio >= 2.0;

  const anomalyInfo: VolumeAnomalyInfo = {
    isAnomaly,
    anomalyScore: ratio,
    currentVolume: baseCompany.volume,
    avgVolume20D: avg20D,
    thresholdRatio: 2.0,
    interpretation: isAnomaly
      ? `High Volume Anomaly Detected: Intraday trading is ${ratio}x higher than the 20-day trailing average volume. Signals institutional positioning or bloc trading.`
      : `Normal Order Flow: Trading volume is within ${ratio}x of 20-day trailing baseline.`,
  };

  // Estimated Buy / Sell pressure info
  const buyPercent = baseCompany.buyPressure || 62;
  const sellPercent = 100 - buyPercent;
  const totalShares = baseCompany.volume;
  const buyVolume = Math.round((totalShares * buyPercent) / 100);
  const sellVolume = totalShares - buyVolume;

  const pressureInfo: BuySellPressureInfo = {
    buyPercent,
    sellPercent,
    buyVolume,
    sellVolume,
    status:
      buyPercent >= 65
        ? 'Heavy Accumulation'
        : buyPercent >= 55
        ? 'Mild Accumulation'
        : buyPercent <= 35
        ? 'Heavy Distribution'
        : buyPercent <= 45
        ? 'Mild Distribution'
        : 'Neutral',
    methodologyNote:
      'Estimated based on trade execution price relative to the prevailing bid/ask spread from floorsheet tick records.',
  };

  // 52-week statistics
  const week52High = Math.round(baseCompany.price * 1.34);
  const week52Low = Math.round(baseCompany.price * 0.72);
  const eps = baseCompany.sector === 'Hydropower' ? undefined : Math.round((baseCompany.price / (baseCompany.peRatio || 18)) * 10) / 10;
  const bookValue = Math.round(baseCompany.price * 0.45);

  const relatedNews = MOCK_NEWS_FEED.filter(
    (n) => n.relatedCompanies.includes(baseCompany.symbol) || n.relatedCompanies.length === 0
  );

  return {
    ...baseCompany,
    week52High,
    week52Low,
    eps,
    bookValue,
    sharesOutstanding: Math.round(baseCompany.turnover / baseCompany.price * 120),
    paidUpCapital: Math.round((baseCompany.marketCap || 50000000000) * 0.8),
    historicalData: history,
    brokerBreakdown,
    anomalyInfo,
    pressureInfo,
    relatedNews,
  };
}
