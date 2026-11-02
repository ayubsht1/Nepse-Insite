export interface PeerComparisonMetric {
  symbol: string;
  name: string;
  sector: string;
  ltp: number;
  dailyReturn: number;
  periodReturn: number; // 30D return %
  volume: number;
  turnoverCr: number;
  volatilityBeta: number;
  newsCount: number;
  peRatio?: number;
  buyPressure: number;
}

export const COMPARISON_PEERS: PeerComparisonMetric[] = [
  {
    symbol: 'NABIL',
    name: 'Nabil Bank Limited',
    sector: 'Commercial Bank',
    ltp: 524.0,
    dailyReturn: 1.65,
    periodReturn: 6.8,
    volume: 184500,
    turnoverCr: 9.63,
    volatilityBeta: 1.12,
    newsCount: 14,
    peRatio: 16.4,
    buyPressure: 68,
  },
  {
    symbol: 'GBIME',
    name: 'Global IME Bank Limited',
    sector: 'Commercial Bank',
    ltp: 242.0,
    dailyReturn: 1.34,
    periodReturn: 4.2,
    volume: 245800,
    turnoverCr: 5.95,
    volatilityBeta: 0.95,
    newsCount: 9,
    peRatio: 12.8,
    buyPressure: 59,
  },
  {
    symbol: 'CIT',
    name: 'Citizen Investment Trust',
    sector: 'Investment',
    ltp: 2480.0,
    dailyReturn: -1.0,
    periodReturn: -3.4,
    volume: 38200,
    turnoverCr: 9.47,
    volatilityBeta: 1.45,
    newsCount: 6,
    peRatio: 32.1,
    buyPressure: 42,
  },
  {
    symbol: 'NTC',
    name: 'Nepal Telecom (NTC)',
    sector: 'Telecom',
    ltp: 885.0,
    dailyReturn: 0.57,
    periodReturn: 2.1,
    volume: 92400,
    turnoverCr: 8.18,
    volatilityBeta: 0.72,
    newsCount: 18,
    peRatio: 14.2,
    buyPressure: 55,
  },
  {
    symbol: 'SHIVM',
    name: 'Shivam Cements Limited',
    sector: 'Manufacturing',
    ltp: 578.0,
    dailyReturn: -2.03,
    periodReturn: -5.8,
    volume: 312000,
    turnoverCr: 18.13,
    volatilityBeta: 2.34,
    newsCount: 11,
    peRatio: 41.5,
    buyPressure: 38,
  },
  {
    symbol: 'HDL',
    name: 'Himalayan Distillery Limited',
    sector: 'Manufacturing',
    ltp: 1680.0,
    dailyReturn: 2.07,
    periodReturn: 12.4,
    volume: 68400,
    turnoverCr: 11.49,
    volatilityBeta: 1.88,
    newsCount: 5,
    peRatio: 38.6,
    buyPressure: 72,
  },
  {
    symbol: 'UPPER',
    name: 'Upper Tamakoshi Hydropower',
    sector: 'Hydropower',
    ltp: 218.0,
    dailyReturn: -2.02,
    periodReturn: -8.2,
    volume: 489000,
    turnoverCr: 10.66,
    volatilityBeta: 2.15,
    newsCount: 8,
    peRatio: 52.0,
    buyPressure: 44,
  },
  {
    symbol: 'CHCL',
    name: 'Chilime Hydropower Company',
    sector: 'Hydropower',
    ltp: 512.0,
    dailyReturn: 1.19,
    periodReturn: 3.5,
    volume: 114200,
    turnoverCr: 5.85,
    volatilityBeta: 1.3,
    newsCount: 7,
    peRatio: 22.4,
    buyPressure: 61,
  },
];

// Time series of normalized % return starting from 0%
export const NORMALIZED_PERFORMANCE_30D = [
  { date: 'Oct 02', NABIL: 0.0, GBIME: 0.0, CIT: 0.0, SHIVM: 0.0, HDL: 0.0, UPPER: 0.0 },
  { date: 'Oct 05', NABIL: 1.2, GBIME: 0.8, CIT: -0.5, SHIVM: 2.1, HDL: 3.4, UPPER: -1.2 },
  { date: 'Oct 09', NABIL: 0.9, GBIME: 1.4, CIT: -1.2, SHIVM: 1.5, HDL: 4.8, UPPER: -2.4 },
  { date: 'Oct 12', NABIL: 2.4, GBIME: 2.1, CIT: -0.8, SHIVM: -0.8, HDL: 5.2, UPPER: -3.8 },
  { date: 'Oct 17', NABIL: 3.1, GBIME: 2.5, CIT: -2.1, SHIVM: -2.4, HDL: 6.9, UPPER: -4.5 },
  { date: 'Oct 22', NABIL: 4.5, GBIME: 3.2, CIT: -1.8, SHIVM: -3.6, HDL: 8.4, UPPER: -6.1 },
  { date: 'Oct 26', NABIL: 4.8, GBIME: 3.6, CIT: -2.5, SHIVM: -4.2, HDL: 9.8, UPPER: -7.2 },
  { date: 'Oct 31', NABIL: 5.6, GBIME: 3.9, CIT: -2.9, SHIVM: -5.1, HDL: 10.5, UPPER: -7.8 },
  { date: 'Nov 06', NABIL: 6.2, GBIME: 4.0, CIT: -3.1, SHIVM: -4.9, HDL: 11.2, UPPER: -8.0 },
  { date: 'Nov 12', NABIL: 6.8, GBIME: 4.2, CIT: -3.4, SHIVM: -5.8, HDL: 12.4, UPPER: -8.2 },
];
