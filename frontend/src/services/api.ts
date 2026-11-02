import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from 'axios';

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || '/api').replace(/\/$/, '');
const ACCESS_TOKEN_KEY = 'auth_token';
const LEGACY_REFRESH_TOKEN_KEY = 'refresh_token';

interface RetriableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

export interface ApiUser {
  id: number;
  username: string;
  first_name: string;
  email: string;
  role: 'admin' | 'analyst' | 'viewer';
}

export interface ApiPage<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiCompany {
  id: number;
  symbol: string;
  name: string;
  aliases: string[];
  sector: string;
  is_active: boolean;
}

export interface ApiStockPrice {
  id: number;
  company: number;
  symbol: string;
  date: string;
  open_price: string;
  high_price: string;
  low_price: string;
  close_price: string;
  volume: number;
  source: string;
}

export interface ApiNewsTag {
  company: ApiCompany;
  confidence_score: string;
  method: 'rule' | 'analyst';
  updated_at: string;
}

export interface ApiNewsArticle {
  id: number;
  url: string;
  source: string;
  headline: string;
  body: string;
  published_at: string | null;
  collected_at: string;
  company_tags: ApiNewsTag[];
}

export interface ApiNewsCorrection {
  id: number;
  corrected_by: string;
  previous_tags: Array<{
    company_id: number;
    symbol: string;
    confidence_score: string;
    method: string;
  }>;
  corrected_tags: Array<{
    company_id: number;
    symbol: string;
    confidence_score: string;
    method: string;
  }>;
  note: string;
  created_at: string;
}

export interface ApiCrawlSource {
  id: number;
  name: string;
  key: string;
  enabled: boolean;
}

export interface ApiCrawlRun {
  id: number;
  source: number | null;
  source_name: string | null;
  triggered_by: string | null;
  status: 'queued' | 'running' | 'succeeded' | 'partial' | 'failed';
  task_id: string;
  started_at: string | null;
  finished_at: string | null;
  requests_made: number;
  articles_created: number;
  articles_duplicates: number;
  error_message: string;
  created_at: string;
}

export interface ApiCompanyBehavior {
  company: { id: number; symbol: string; name: string };
  period: { from: string; to: string };
  price_change_percent: string | null;
  latest_price: { date: string; close: string; volume: number } | null;
  vwap: {
    available: boolean;
    value: string | null;
    method: string;
    transactions: number;
    limitation: string | null;
  };
  latest_pressure_indicator: {
    available: boolean;
    score?: string;
    method?: string;
    volume?: number;
    interpretation?: string;
  };
  latest_volume_anomaly: {
    available: boolean;
    date?: string;
    volume?: number;
    prior_trading_days?: number;
    prior_average_volume?: string;
    ratio_to_average?: string | null;
    threshold_multiplier?: string;
    is_anomaly?: boolean;
    reason?: string;
  };
  floorsheet: {
    available: boolean;
    transactions: number;
    quantity: number;
    turnover: string;
    brokers: {
      available: boolean;
      brokers: Array<{
        broker_code: string;
        buy_quantity: number;
        sell_quantity: number;
        buy_turnover: string;
        sell_turnover: string;
      }>;
      limitation: string;
    };
  };
  news_relationship: {
    observations: Array<Record<string, unknown>>;
    method: string;
    limitation: string;
  };
}

export interface ApiError extends Error {
  status?: number;
  data?: unknown;
}

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

function getCsrfToken() {
  if (typeof document === 'undefined') return null;
  const token = document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('csrftoken='))
    ?.slice('csrftoken='.length);
  return token ? decodeURIComponent(token) : null;
}

apiClient.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const csrfToken = getCsrfToken();
    if (csrfToken) config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

let refreshRequest: Promise<string> | null = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableRequestConfig | undefined;
    const isAuthEndpoint = config?.url?.includes('/auth/');

    if (
      error.response?.status === 401 &&
      config &&
      !config._retry &&
      !isAuthEndpoint &&
      getAccessToken()
    ) {
      config._retry = true;
      refreshRequest ??= axios
        .post<{ access: string }>(
          `${API_BASE_URL}/auth/token/refresh/`,
          {},
          {
            timeout: 15000,
            withCredentials: true,
            headers: getCsrfToken()
              ? { 'X-CSRFToken': getCsrfToken() }
              : undefined,
          },
        )
        .then(({ data }) => {
          window.sessionStorage.setItem(ACCESS_TOKEN_KEY, data.access);
          return data.access;
        })
        .finally(() => {
          refreshRequest = null;
        });

      try {
        const accessToken = await refreshRequest;
        config.headers.Authorization = `Bearer ${accessToken}`;
        return apiClient(config);
      } catch (refreshError) {
        clearAuthTokens();
        window.dispatchEvent(new Event('auth:expired'));
        return Promise.reject(refreshError);
      }
    }

    const data = error.response?.data as
      | { detail?: string; message?: string }
      | undefined;
    const apiError: ApiError = new Error(
      data?.detail || data?.message || error.message,
    );
    apiError.status = error.response?.status;
    apiError.data = error.response?.data;
    return Promise.reject(apiError);
  },
);

export function storeAuthTokens(tokens: { access: string }) {
  window.sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
}

export function clearAuthTokens() {
  if (typeof window !== 'undefined') {
    window.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(LEGACY_REFRESH_TOKEN_KEY);
  }
}

export function getAccessToken() {
  return typeof window === 'undefined'
    ? null
    : window.sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export async function login(username: string, password: string) {
  await ensureCsrfCookie();
  const { data } = await apiClient.post<{ access: string }>(
    '/auth/token/',
    { username, password },
  );
  storeAuthTokens(data);
}

export async function register(input: {
  username: string;
  first_name: string;
  email: string;
  password: string;
}) {
  await ensureCsrfCookie();
  const { data } = await apiClient.post<ApiUser>('/auth/register/', input);
  return data;
}

export async function logout() {
  try {
    await apiClient.post('/auth/logout/', {});
  } finally {
    clearAuthTokens();
  }
}

async function ensureCsrfCookie() {
  await apiClient.get('/auth/csrf/');
}

export async function fetchCurrentUser() {
  const { data } = await apiClient.get<ApiUser>('/users/me/');
  return data;
}

async function getResults<T>(url: string, params?: Record<string, unknown>) {
  const { data } = await apiClient.get<ApiPage<T> | T[]>(url, { params });
  return Array.isArray(data) ? data : data.results;
}

export async function fetchCompanies(params: {
  search?: string;
  sector?: string;
  page?: number;
} = {}) {
  const { data } = await apiClient.get<ApiPage<ApiCompany> | ApiCompany[]>(
    '/companies/',
    { params },
  );
  return Array.isArray(data)
    ? { count: data.length, next: null, previous: null, results: data }
    : data;
}

export async function fetchCompanyPrices(
  companyId: number,
  range: '7d' | '15d' | '30d' = '30d',
) {
  return getResults<ApiStockPrice>(`/companies/${companyId}/prices/`, { range });
}

export async function fetchNews(params: {
  companyId?: number;
  source?: string;
  search?: string;
  page?: number;
} = {}) {
  return getResults<ApiNewsArticle>('/news/', {
    company_id: params.companyId,
    source: params.source,
    search: params.search,
    page: params.page,
  });
}

export async function fetchNewsCorrections(articleId: number) {
  return getResults<ApiNewsCorrection>(`/news/${articleId}/corrections/`);
}

export async function recategorizeNews(
  articleId: number,
  tags: Array<{ company_id: number; confidence_score: string }>,
  note: string,
) {
  const { data } = await apiClient.post<ApiNewsArticle>(
    `/news/${articleId}/recategorize/`,
    { tags, note },
  );
  return data;
}

export async function fetchCompanyBehaviorSummary(
  companyId: number,
  range: '7d' | '15d' | '30d' = '30d',
) {
  const { data } = await apiClient.get<ApiCompanyBehavior>(
    `/companies/${companyId}/behavior-summary/`,
    { params: { range } },
  );
  return data;
}

export async function compareCompanies(
  companyIds: number[],
  range: '7d' | '15d' | '30d' = '30d',
) {
  const { data } = await apiClient.get<{
    period: { from: string; to: string };
    companies: ApiCompanyBehavior[];
  }>('/companies/compare/', {
    params: { ids: companyIds.join(','), range },
  });
  return data;
}

export async function fetchCrawlSources() {
  return getResults<ApiCrawlSource>('/admin/crawl-sources/');
}

export async function fetchCrawlRuns(status?: string) {
  return getResults<ApiCrawlRun>('/admin/crawl-runs/', { status });
}

export async function triggerCrawlRun(sourceIds?: number[]) {
  const { data } = await apiClient.post<{ runs: ApiCrawlRun[] }>(
    '/admin/crawl-runs/',
    sourceIds?.length ? { source_ids: sourceIds } : {},
  );
  return data.runs;
}

export async function fetchAdminUsers() {
  return getResults<ApiUser>('/admin/users/');
}

export async function updateUserRole(
  userId: number,
  role: ApiUser['role'],
) {
  const { data } = await apiClient.patch<ApiUser>(`/admin/users/${userId}/`, {
    role,
  });
  return data;
}

export async function createCompany(input: {
  symbol: string;
  name: string;
  aliases: string[];
  sector: string;
}) {
  const { data } = await apiClient.post<ApiCompany>('/companies/', input);
  return data;
}

export async function updateCompany(
  companyId: number,
  input: Partial<ApiCompany>,
) {
  const { data } = await apiClient.patch<ApiCompany>(
    `/companies/${companyId}/`,
    input,
  );
  return data;
}

export { apiClient };
