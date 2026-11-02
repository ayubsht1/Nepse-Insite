export type UserRole = 'admin' | 'analyst' | 'viewer';

export type NavigationTab =
  | 'overview'
  | 'companies'
  | 'market-analysis'
  | 'news-intelligence'
  | 'comparison'
  | 'admin-panel'
  | 'settings';

export interface Company {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  changePercent: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  turnover: number;
  vwap: number;
  peRatio?: number;
  marketCap?: number;
  newsCount?: number;
  volatility?: number; // e.g. standard deviation or beta
  buyPressure?: number; // 0 - 100 percentage
}

export interface CompanyHistoricalOHLCV {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  vwap: number;
}

export interface BrokerTradeSummary {
  brokerNumber: number;
  brokerName: string;
  buyVolume: number;
  buyAmount: number;
  sellVolume: number;
  sellAmount: number;
  netShares: number;
  netAmount: number;
}

export interface VolumeAnomalyInfo {
  isAnomaly: boolean;
  anomalyScore: number; // e.g. 2.4x
  currentVolume: number;
  avgVolume20D: number;
  thresholdRatio: number;
  interpretation: string;
}

export interface BuySellPressureInfo {
  buyPercent: number; // e.g. 64%
  sellPercent: number; // e.g. 36%
  buyVolume: number;
  sellVolume: number;
  status: 'Heavy Accumulation' | 'Mild Accumulation' | 'Neutral' | 'Mild Distribution' | 'Heavy Distribution';
  methodologyNote: string;
}

export interface CompanyDetails extends Company {
  week52High: number;
  week52Low: number;
  eps?: number;
  bookValue?: number;
  sharesOutstanding: number;
  paidUpCapital: number;
  historicalData: Record<'7D' | '15D' | '30D', CompanyHistoricalOHLCV[]>;
  brokerBreakdown: BrokerTradeSummary[];
  anomalyInfo: VolumeAnomalyInfo;
  pressureInfo: BuySellPressureInfo;
  relatedNews: MarketNewsItem[];
}

export interface MarketIndex {
  symbol: string;
  name: string;
  value: number;
  change: number;
  changePercent: number;
  turnover?: string;
}

export interface MarketStatus {
  isOpen: boolean;
  dateStr: string;
  dateNepali: string;
  timeNPT: string;
  nextSession: string;
}

export interface NewsTagCorrection {
  id: string;
  articleId: string;
  articleTitle: string;
  analystName: string;
  analystRole: UserRole;
  timestamp: string;
  previousTags: string[];
  correctedTags: string[];
  previousCategory: string;
  correctedCategory: string;
  reason?: string;
}

export interface MarketNewsItem {
  id: string;
  headline: string;
  excerpt: string;
  content?: string;
  source: 'Bizmandu' | 'Sharesansar' | 'OnlineKhabar' | 'Merolagani';
  publishedAt: string;
  relatedCompanies: string[]; // Ticker symbols
  category: 'Earnings' | 'Policy' | 'Dividend' | 'Hydropower' | 'Listing' | 'Banking' | 'Economy';
  confidence: number; // 0 to 1 score (e.g. 0.94)
  url?: string;
  isManuallyCorrected?: boolean;
  lastCorrectedBy?: string;
  correctionHistory?: NewsTagCorrection[];
}


export interface MarketActivityPoint {
  time: string;
  nepse: number;
  sensitive: number;
  volume: number; // in thousand shares
  turnover: number; // in Cr NPR
}

export interface SectorPerformance {
  sector: string;
  changePercent: number;
  turnoverArba: number;
}

export interface NotificationItem {
  id: string;
  title: string;
  excerpt: string;
  type: 'news' | 'market' | 'circuit' | 'disclosure';
  timestamp: string;
  read: boolean;
  relatedSymbol?: string;
}

export interface UserProfile {
  name: string;
  email: string;
  role: UserRole;
  avatarUrl?: string;
  brokerAffiliation?: string;
}

export interface CrawlRun {
  id: string;
  source: 'All Portals' | 'Bizmandu' | 'Sharesansar' | 'OnlineKhabar' | 'Merolagani';
  startTime: string;
  completionTime: string;
  duration: string;
  status: 'Completed' | 'Running' | 'Failed' | 'Warning';
  articlesCollected: number;
  errorsCount: number;
  triggeredBy: string;
}

export interface CrawlLog {
  id: string;
  runId: string;
  timestamp: string;
  level: 'error' | 'warning' | 'info';
  source: string;
  message: string;
}

export interface ManagedUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: 'active' | 'inactive';
  brokerAffiliation: string;
  lastActive: string;
}

export interface ManagedCompany {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  turnover: number;
  vwap: number;
  isActive: boolean;
  isInWatchlist: boolean;
}

