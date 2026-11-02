'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  ApiCompany,
  ApiNewsArticle,
  ApiNewsCorrection,
  fetchCompanies,
  fetchNews,
  fetchNewsCorrections,
  recategorizeNews,
} from '../../services/api';
import { useApp } from '../../context/AppContext';
import { DataTable, EmptyState, LoadingState, PageHeader } from '../../components/ui';
import { Column } from '../../components/ui/DataTable';
import { Newspaper } from 'lucide-react';

export const NewsIntelligenceView: React.FC = () => {
  const { userRole } = useApp();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [source, setSource] = useState('');
  const [selectedArticle, setSelectedArticle] = useState<ApiNewsArticle | null>(
    null,
  );
  const [historyArticleId, setHistoryArticleId] = useState<number | null>(null);
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<number[]>([]);
  const [confidenceByCompany, setConfidenceByCompany] = useState<
    Record<number, string>
  >({});
  const [note, setNote] = useState('');
  const canEdit = userRole === 'admin' || userRole === 'analyst';

  const newsQuery = useQuery({
    queryKey: ['news', search, source],
    queryFn: () =>
      fetchNews({
        search: search || undefined,
        source: source || undefined,
      }),
  });
  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: () => fetchCompanies(),
  });
  const historyQuery = useQuery({
    queryKey: ['news-corrections', historyArticleId],
    queryFn: () => fetchNewsCorrections(historyArticleId!),
    enabled: historyArticleId !== null,
  });
  const correctionMutation = useMutation({
    mutationFn: async () => {
      if (!selectedArticle) throw new Error('Select an article to correct.');
      const tags = selectedCompanyIds.map((companyId) => {
        const score = confidenceByCompany[companyId];
        if (!score || !Number.isFinite(Number(score))) {
          throw new Error('Enter a confidence score for every selected company.');
        }
        return { company_id: companyId, confidence_score: score };
      });
      return recategorizeNews(selectedArticle.id, tags, note);
    },
    onSuccess: async () => {
      toast.success('News company tags updated.');
      setSelectedArticle(null);
      setNote('');
      await queryClient.invalidateQueries({ queryKey: ['news'] });
      await queryClient.invalidateQueries({ queryKey: ['news-corrections'] });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Unable to save correction.');
    },
  });

  const articles = newsQuery.data ?? [];
  const companies = companiesQuery.data?.results ?? [];
  const sources = useMemo(
    () => [...new Set(articles.map((article) => article.source))].sort(),
    [articles],
  );
  const columns: Column<ApiNewsArticle>[] = [
    {
      key: 'headline',
      header: 'Headline',
      render: (article) => (
        <div className="max-w-2xl">
          <a
            href={article.url}
            target="_blank"
            rel="noreferrer"
            className="font-semibold text-slate-900 hover:text-emerald-600 dark:text-slate-100 dark:hover:text-emerald-400"
          >
            {article.headline}
          </a>
          <p className="mt-1 line-clamp-2 text-[11px] text-slate-500">
            {article.body || 'The source did not provide article text.'}
          </p>
        </div>
      ),
    },
    {
      key: 'source',
      header: 'Source',
      render: (article) => (
        <span className="whitespace-nowrap text-xs">{article.source}</span>
      ),
    },
    {
      key: 'published_at',
      header: 'Published',
      render: (article) => (
        <span className="whitespace-nowrap text-xs">
          {article.published_at
            ? new Date(article.published_at).toLocaleString()
            : 'Date unavailable'}
        </span>
      ),
    },
    {
      key: 'company_tags',
      header: 'Company tags',
      render: (article) => (
        <div className="flex min-w-32 flex-wrap gap-1">
          {article.company_tags.length ? (
            article.company_tags.map((tag) => (
              <span
                key={tag.company.id}
                title={`${tag.method} match, confidence ${tag.confidence_score}`}
                className="rounded border border-slate-200 px-1.5 py-0.5 font-mono text-[10px] dark:border-slate-700"
              >
                {tag.company.symbol} · {Math.round(Number(tag.confidence_score) * 100)}%
              </span>
            ))
          ) : (
            <span className="text-xs text-slate-500">No company match</span>
          )}
        </div>
      ),
    },
    {
      key: 'actions',
      header: 'Review',
      render: (article) => (
        <div className="flex gap-2 whitespace-nowrap">
          {canEdit && (
            <button
              onClick={() => {
                setSelectedArticle(article);
                setSelectedCompanyIds(
                  article.company_tags.map((tag) => tag.company.id),
                );
                setConfidenceByCompany(
                  Object.fromEntries(
                    article.company_tags.map((tag) => [
                      tag.company.id,
                      tag.confidence_score,
                    ]),
                  ),
                );
                setNote('');
              }}
              className="rounded bg-emerald-600 px-2 py-1 text-[11px] font-semibold text-white"
            >
              Correct tags
            </button>
          )}
          <button
            onClick={() => setHistoryArticleId(article.id)}
            className="rounded border border-slate-300 px-2 py-1 text-[11px] dark:border-slate-700"
          >
            History
          </button>
        </div>
      ),
    },
  ];

  useEffect(() => {
    if (historyArticleId === null || historyQuery.isLoading || historyQuery.isError) {
      return;
    }
    const corrections: ApiNewsCorrection[] = historyQuery.data ?? [];
    if (corrections.length === 0) {
      toast.info('No analyst corrections have been recorded for this article.');
    }
  }, [historyArticleId, historyQuery.data, historyQuery.isError, historyQuery.isLoading]);

  return (
    <div className="space-y-5">
      <PageHeader
        title="Financial News Intelligence"
        description="News collected from configured sources, with rule-based company matches and analyst correction history. Topic categories are not assigned by the backend."
        icon={Newspaper}
      />

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-[#111827] sm:flex-row">
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search headlines and article text"
          className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
        />
        <select
          value={source}
          onChange={(event) => setSource(event.target.value)}
          className="rounded-lg border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
        >
          <option value="">All available sources</option>
          {sources.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      {newsQuery.isLoading ? (
        <LoadingState message="Loading collected news…" />
      ) : newsQuery.isError ? (
        <p role="alert" className="rounded-lg bg-rose-50 p-4 text-sm text-rose-700">
          {newsQuery.error.message}
        </p>
      ) : articles.length === 0 ? (
        <EmptyState
          title="No collected articles"
          description="No matching articles are stored yet. The news feed will populate when an enabled, robots-compliant source completes a crawl."
        />
      ) : (
        <DataTable
          columns={columns}
          data={articles}
          keyExtractor={(article) => article.id}
          emptyMessage="No collected articles match these filters."
        />
      )}

      {companiesQuery.isError && (
        <p role="alert" className="text-sm text-rose-600">
          Unable to load companies for news corrections: {companiesQuery.error.message}
        </p>
      )}

      {historyArticleId !== null && (
        <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827]">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Correction history · Article {historyArticleId}</h2>
            <button
              onClick={() => setHistoryArticleId(null)}
              className="text-sm text-slate-500 hover:text-slate-900 dark:hover:text-white"
            >
              Close
            </button>
          </div>
          {historyQuery.isLoading ? (
            <LoadingState message="Loading correction history…" />
          ) : historyQuery.isError ? (
            <p role="alert" className="mt-3 text-sm text-rose-600">
              {historyQuery.error.message}
            </p>
          ) : historyQuery.data?.length ? (
            <ul className="mt-3 divide-y divide-slate-200 dark:divide-slate-800">
              {historyQuery.data.map((correction) => (
                <li key={correction.id} className="space-y-1 py-3 text-xs">
                  <p className="font-medium">
                    {correction.corrected_by} ·{' '}
                    {new Date(correction.created_at).toLocaleString()}
                  </p>
                  <p className="text-slate-500">{correction.note}</p>
                  <p>
                    {correction.previous_tags.map((tag) => tag.symbol).join(', ') || 'No tags'}
                    {' → '}
                    {correction.corrected_tags.map((tag) => tag.symbol).join(', ') || 'No tags'}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-500">
              No correction history is available.
            </p>
          )}
        </section>
      )}

      {selectedArticle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              correctionMutation.mutate();
            }}
            className="max-h-[90vh] w-full max-w-2xl space-y-4 overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-[#111827]"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-semibold">Correct company tags</h2>
                <p className="mt-1 text-xs text-slate-500">{selectedArticle.headline}</p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedArticle(null)}
                className="text-sm text-slate-500"
              >
                Close
              </button>
            </div>
            {companiesQuery.isLoading ? (
              <LoadingState message="Loading companies…" />
            ) : (
              <div className="max-h-64 space-y-2 overflow-y-auto">
                {companies.map((company: ApiCompany) => {
                  const checked = selectedCompanyIds.includes(company.id);
                  return (
                    <label
                      key={company.id}
                      className="flex items-center gap-3 rounded-lg border border-slate-200 p-2 text-sm dark:border-slate-700"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(event) => {
                          setSelectedCompanyIds((current) =>
                            event.target.checked
                              ? [...current, company.id]
                              : current.filter((id) => id !== company.id),
                          );
                        }}
                      />
                      <span className="flex-1">
                        <span className="font-mono font-semibold">{company.symbol}</span>
                        <span className="ml-2 text-slate-500">{company.name}</span>
                      </span>
                      {checked && (
                        <input
                          type="number"
                          aria-label={`${company.symbol} confidence score`}
                          min="0"
                          max="1"
                          step="0.001"
                          required
                          value={confidenceByCompany[company.id] ?? ''}
                          onChange={(event) =>
                            setConfidenceByCompany((current) => ({
                              ...current,
                              [company.id]: event.target.value,
                            }))
                          }
                          className="w-24 rounded border border-slate-300 bg-transparent px-2 py-1 text-xs dark:border-slate-600"
                          placeholder="0–1 score"
                        />
                      )}
                    </label>
                  );
                })}
              </div>
            )}
            <label className="block text-sm">
              Correction note
              <textarea
                required
                minLength={3}
                maxLength={2000}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                className="mt-1 min-h-20 w-full rounded-lg border border-slate-300 bg-transparent p-2 dark:border-slate-700"
              />
            </label>
            <button
              type="submit"
              disabled={
                !canEdit ||
                correctionMutation.isPending ||
                companiesQuery.isLoading
              }
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {correctionMutation.isPending ? 'Saving…' : 'Save correction'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
