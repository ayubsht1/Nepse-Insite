export interface BrokerFlowSummary {
  brokerNumber: number;
  brokerName: string;
  totalTurnover: number;
  totalVolume: number;
  topBoughtStock: string;
  topSoldStock: string;
  netTurnover: number; // positive = net buyer, negative = net seller
  status: 'Accumulator' | 'Distributor';
}

export interface VolumeAnomalyEntry {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  ltp: number;
  changePercent: number;
  todayVolume: number;
  avgVolume20D: number;
  ratio: number;
  turnoverCr: number;
  status: 'Critical Surge' | 'Moderate Anomaly' | 'Watchlist Alert';
}

export interface NewsImpactCorrelationPoint {
  date: string;
  articleCount: number;
  avgSentimentScore: number; // 0 to 1
  nextDayReturnPercent: number;
}

export const TOP_BUYING_BROKERS: BrokerFlowSummary[] = [
  {
    brokerNumber: 58,
    brokerName: 'Online Securities Ltd.',
    totalTurnover: 845000000,
    totalVolume: 1420000,
    topBoughtStock: 'NABIL',
    topSoldStock: 'UPPER',
    netTurnover: 320000000,
    status: 'Accumulator',
  },
  {
    brokerNumber: 45,
    brokerName: 'Imperial Securities Co.',
    totalTurnover: 692000000,
    totalVolume: 1180000,
    topBoughtStock: 'SHIVM',
    topSoldStock: 'NICA',
    netTurnover: 215000000,
    status: 'Accumulator',
  },
  {
    brokerNumber: 49,
    brokerName: 'Online Securities Broker 49',
    totalTurnover: 540000000,
    totalVolume: 920000,
    topBoughtStock: 'HDL',
    topSoldStock: 'GBIME',
    netTurnover: 184000000,
    status: 'Accumulator',
  },
  {
    brokerNumber: 42,
    brokerName: 'Sani Securities Co. Ltd.',
    totalTurnover: 480000000,
    totalVolume: 810000,
    topBoughtStock: 'CIT',
    topSoldStock: 'CHCL',
    netTurnover: 142000000,
    status: 'Accumulator',
  },
];

export const TOP_SELLING_BROKERS: BrokerFlowSummary[] = [
  {
    brokerNumber: 19,
    brokerName: 'Nepal Stock House Pvt. Ltd.',
    totalTurnover: 780000000,
    totalVolume: 1350000,
    topBoughtStock: 'NTC',
    topSoldStock: 'SHIVM',
    netTurnover: -290000000,
    status: 'Distributor',
  },
  {
    brokerNumber: 28,
    brokerName: 'Shrikrishna Securities Ltd.',
    totalTurnover: 610000000,
    totalVolume: 1040000,
    topBoughtStock: 'GBIME',
    topSoldStock: 'NABIL',
    netTurnover: -198000000,
    status: 'Distributor',
  },
  {
    brokerNumber: 34,
    brokerName: 'Vision Securities Pvt. Ltd.',
    totalTurnover: 530000000,
    totalVolume: 890000,
    topBoughtStock: 'UPPER',
    topSoldStock: 'HDL',
    netTurnover: -165000000,
    status: 'Distributor',
  },
  {
    brokerNumber: 57,
    brokerName: 'Aryatara Investment & Securities',
    totalTurnover: 440000000,
    totalVolume: 740000,
    topBoughtStock: 'CHCL',
    topSoldStock: 'CIT',
    netTurnover: -124000000,
    status: 'Distributor',
  },
];

export const VOLUME_ANOMALIES: VolumeAnomalyEntry[] = [
  {
    id: 'anom-1',
    symbol: 'SHIVM',
    name: 'Shivam Cements Limited',
    sector: 'Manufacturing',
    ltp: 578.0,
    changePercent: -2.03,
    todayVolume: 312000,
    avgVolume20D: 112000,
    ratio: 2.78,
    turnoverCr: 18.12,
    status: 'Critical Surge',
  },
  {
    id: 'anom-2',
    symbol: 'UPPER',
    name: 'Upper Tamakoshi Hydropower',
    sector: 'Hydropower',
    ltp: 218.0,
    changePercent: -2.02,
    todayVolume: 489000,
    avgVolume20D: 198000,
    ratio: 2.47,
    turnoverCr: 10.66,
    status: 'Critical Surge',
  },
  {
    id: 'anom-3',
    symbol: 'HDL',
    name: 'Himalayan Distillery Limited',
    sector: 'Manufacturing',
    ltp: 1680.0,
    changePercent: 2.07,
    todayVolume: 68400,
    avgVolume20D: 29500,
    ratio: 2.32,
    turnoverCr: 11.49,
    status: 'Moderate Anomaly',
  },
  {
    id: 'anom-4',
    symbol: 'NABIL',
    name: 'Nabil Bank Limited',
    sector: 'Commercial Bank',
    ltp: 524.0,
    changePercent: 1.65,
    todayVolume: 184500,
    avgVolume20D: 91000,
    ratio: 2.03,
    turnoverCr: 9.63,
    status: 'Moderate Anomaly',
  },
  {
    id: 'anom-5',
    symbol: 'NICA',
    name: 'NIC Asia Bank Limited',
    sector: 'Commercial Bank',
    ltp: 432.0,
    changePercent: -0.35,
    todayVolume: 162000,
    avgVolume20D: 94000,
    ratio: 1.72,
    turnoverCr: 6.99,
    status: 'Watchlist Alert',
  },
];

export const NEWS_IMPACT_SERIES: NewsImpactCorrelationPoint[] = [
  { date: 'Session 1', articleCount: 14, avgSentimentScore: 0.72, nextDayReturnPercent: 0.85 },
  { date: 'Session 2', articleCount: 22, avgSentimentScore: 0.84, nextDayReturnPercent: 1.42 },
  { date: 'Session 3', articleCount: 9, avgSentimentScore: 0.51, nextDayReturnPercent: -0.22 },
  { date: 'Session 4', articleCount: 18, avgSentimentScore: 0.65, nextDayReturnPercent: 0.68 },
  { date: 'Session 5', articleCount: 31, avgSentimentScore: 0.88, nextDayReturnPercent: 1.84 },
  { date: 'Session 6', articleCount: 12, avgSentimentScore: 0.44, nextDayReturnPercent: -0.65 },
  { date: 'Session 7', articleCount: 26, avgSentimentScore: 0.78, nextDayReturnPercent: 0.95 },
];

export const SECTOR_VWAP_COMPARISON = [
  { sector: 'Commercial Banks', closeAvg: 482.4, vwapAvg: 479.8, premiumPercent: 0.54, status: 'Premium' },
  { sector: 'Hotels & Tourism', closeAvg: 5410.2, vwapAvg: 5378.0, premiumPercent: 0.60, status: 'Premium' },
  { sector: 'Non-Life Insurance', closeAvg: 11420.8, vwapAvg: 11340.0, premiumPercent: 0.71, status: 'Premium' },
  { sector: 'Life Insurance', closeAvg: 10240.0, vwapAvg: 10210.0, premiumPercent: 0.29, status: 'Premium' },
  { sector: 'Manufacturing', closeAvg: 1129.0, vwapAvg: 1126.5, premiumPercent: 0.22, status: 'Neutral' },
  { sector: 'Hydropower', closeAvg: 365.0, vwapAvg: 367.8, premiumPercent: -0.76, status: 'Discount' },
  { sector: 'Microfinance', closeAvg: 4890.1, vwapAvg: 4920.4, premiumPercent: -0.62, status: 'Discount' },
];
