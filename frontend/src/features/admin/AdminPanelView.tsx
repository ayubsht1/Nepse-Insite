'use client';

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { PageHeader, EmptyState, LoadingState } from '../../components/ui';
import {
  ApiCrawlRun,
  ApiUser,
  createCompany,
  fetchAdminUsers,
  fetchCompanies,
  fetchCrawlRuns,
  fetchCrawlSources,
  triggerCrawlRun,
  updateCompany,
  updateUserRole,
} from '../../services/api';
import { useApp } from '../../context/AppContext';
import { ShieldCheck } from 'lucide-react';

type AdminTab = 'crawls' | 'companies' | 'users';

export const AdminPanelView: React.FC = () => {
  const { userRole } = useApp();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<AdminTab>('crawls');
  const [sourceId, setSourceId] = useState('');
  const [companyForm, setCompanyForm] = useState({
    symbol: '',
    name: '',
    sector: '',
    aliases: '',
  });
  const [editingCompanyId, setEditingCompanyId] = useState<number | null>(null);

  const runsQuery = useQuery({
    queryKey: ['crawl-runs'],
    queryFn: () => fetchCrawlRuns(),
    refetchInterval: activeTab === 'crawls' ? 5000 : false,
  });
  const sourcesQuery = useQuery({
    queryKey: ['crawl-sources'],
    queryFn: fetchCrawlSources,
  });
  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: () => fetchCompanies(),
  });
  const usersQuery = useQuery({
    queryKey: ['admin-users'],
    queryFn: fetchAdminUsers,
  });

  const refreshAdminData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['crawl-runs'] }),
      queryClient.invalidateQueries({ queryKey: ['companies'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
    ]);
  };
  const crawlMutation = useMutation({
    mutationFn: () =>
      triggerCrawlRun(sourceId ? [Number(sourceId)] : undefined),
    onSuccess: async (runs) => {
      toast.success(`Queued ${runs.length} crawl run(s).`);
      await queryClient.invalidateQueries({ queryKey: ['crawl-runs'] });
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Unable to queue crawl.'),
  });
  const saveCompanyMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        symbol: companyForm.symbol.trim().toUpperCase(),
        name: companyForm.name.trim(),
        sector: companyForm.sector.trim(),
        aliases: companyForm.aliases
          .split(',')
          .map((alias) => alias.trim())
          .filter(Boolean),
      };
      return editingCompanyId
        ? updateCompany(editingCompanyId, payload)
        : createCompany(payload);
    },
    onSuccess: async () => {
      toast.success(editingCompanyId ? 'Company updated.' : 'Company created.');
      setEditingCompanyId(null);
      setCompanyForm({ symbol: '', name: '', sector: '', aliases: '' });
      await queryClient.invalidateQueries({ queryKey: ['companies'] });
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Unable to save company.'),
  });
  const activeMutation = useMutation({
    mutationFn: (company: { id: number; is_active: boolean }) =>
      updateCompany(company.id, { is_active: !company.is_active }),
    onSuccess: refreshAdminData,
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Unable to update company.'),
  });
  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: number; role: ApiUser['role'] }) =>
      updateUserRole(id, role),
    onSuccess: async () => {
      toast.success('Application role updated.');
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : 'Unable to update role.'),
  });

  if (userRole !== 'admin') {
    return (
      <div role="alert" className="rounded-xl border border-rose-300 bg-rose-50 p-6 text-center dark:border-rose-900 dark:bg-rose-950/30">
        <h2 className="font-semibold text-rose-800 dark:text-rose-300">
          Administrator access required
        </h2>
        <p className="mt-2 text-sm text-rose-700 dark:text-rose-400">
          Your application role is {userRole}. Access is also enforced by the backend APIs.
        </p>
      </div>
    );
  }

  const runs = runsQuery.data ?? [];
  const sources = sourcesQuery.data ?? [];
  const companies = companiesQuery.data?.results ?? [];
  const users = usersQuery.data ?? [];
  const error = [runsQuery, sourcesQuery, companiesQuery, usersQuery].find(
    (query) => query.isError,
  )?.error;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Administration"
        description="Manage application roles, company records, and configured news crawls. The backend remains authoritative for all permissions."
        icon={ShieldCheck}
      />
      <nav className="flex flex-wrap gap-2" aria-label="Administration sections">
        {(['crawls', 'companies', 'users'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`rounded-lg px-3 py-2 text-sm capitalize ${
              activeTab === tab
                ? 'bg-emerald-600 text-white'
                : 'border border-slate-300 dark:border-slate-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </nav>

      {error && (
        <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
          {error.message}
        </p>
      )}

      {activeTab === 'crawls' && (
        <section className="space-y-4">
          <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827] sm:flex-row sm:items-end">
            <label className="flex-1 text-sm">
              Enabled source
              <select
                value={sourceId}
                onChange={(event) => setSourceId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
              >
                <option value="">All enabled sources</option>
                {sources
                  .filter((source) => source.enabled)
                  .map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.name}
                    </option>
                  ))}
              </select>
            </label>
            <button
              onClick={() => crawlMutation.mutate()}
              disabled={crawlMutation.isPending || sourcesQuery.isLoading}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {crawlMutation.isPending ? 'Queueing…' : 'Start crawl'}
            </button>
          </div>
          {runsQuery.isLoading ? (
            <LoadingState message="Loading crawl history…" />
          ) : runs.length ? (
            <CrawlRunTable runs={runs} />
          ) : (
            <EmptyState
              title="No crawl history"
              description="No crawl runs have been recorded. Seeded source definitions are disabled until their listings and robots rules are verified."
            />
          )}
        </section>
      )}

      {activeTab === 'companies' && (
        <section className="space-y-4">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              saveCompanyMutation.mutate();
            }}
            className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#111827] sm:grid-cols-2"
          >
            <label className="text-sm">
              Symbol
              <input
                required
                value={companyForm.symbol}
                onChange={(event) =>
                  setCompanyForm({ ...companyForm, symbol: event.target.value })
                }
                className="mt-1 w-full rounded border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
              />
            </label>
            <label className="text-sm">
              Name
              <input
                required
                value={companyForm.name}
                onChange={(event) =>
                  setCompanyForm({ ...companyForm, name: event.target.value })
                }
                className="mt-1 w-full rounded border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
              />
            </label>
            <label className="text-sm">
              Sector
              <input
                value={companyForm.sector}
                onChange={(event) =>
                  setCompanyForm({ ...companyForm, sector: event.target.value })
                }
                className="mt-1 w-full rounded border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
              />
            </label>
            <label className="text-sm">
              Aliases (comma separated)
              <input
                value={companyForm.aliases}
                onChange={(event) =>
                  setCompanyForm({ ...companyForm, aliases: event.target.value })
                }
                className="mt-1 w-full rounded border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
              />
            </label>
            <div className="flex gap-2 sm:col-span-2">
              <button
                type="submit"
                disabled={saveCompanyMutation.isPending}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                {editingCompanyId ? 'Save company' : 'Add company'}
              </button>
              {editingCompanyId && (
                <button
                  type="button"
                  onClick={() => {
                    setEditingCompanyId(null);
                    setCompanyForm({ symbol: '', name: '', sector: '', aliases: '' });
                  }}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm dark:border-slate-700"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
          {companiesQuery.isLoading ? (
            <LoadingState message="Loading company records…" />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="bg-slate-50 dark:bg-[#0e1422]">
                    {['Symbol', 'Name', 'Sector', 'Status', 'Actions'].map((cell) => (
                      <th key={cell} className="px-3 py-2">{cell}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {companies.map((company) => (
                    <tr key={company.id} className="border-t border-slate-200 dark:border-slate-800">
                      <td className="px-3 py-2 font-mono font-semibold">{company.symbol}</td>
                      <td className="px-3 py-2">{company.name}</td>
                      <td className="px-3 py-2">{company.sector || '—'}</td>
                      <td className="px-3 py-2">{company.is_active ? 'Active' : 'Inactive'}</td>
                      <td className="flex gap-2 px-3 py-2">
                        <button
                          onClick={() => {
                            setEditingCompanyId(company.id);
                            setCompanyForm({
                              symbol: company.symbol,
                              name: company.name,
                              sector: company.sector,
                              aliases: company.aliases.join(', '),
                            });
                          }}
                          className="rounded border border-slate-300 px-2 py-1 dark:border-slate-700"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() =>
                            activeMutation.mutate({
                              id: company.id,
                              is_active: company.is_active,
                            })
                          }
                          className="rounded border border-slate-300 px-2 py-1 dark:border-slate-700"
                        >
                          {company.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {activeTab === 'users' && (
        <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-[#111827]">
          {usersQuery.isLoading ? (
            <LoadingState message="Loading users…" />
          ) : users.length ? (
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-50 dark:bg-[#0e1422]">
                  {['Username', 'Email', 'Application role'].map((cell) => (
                    <th key={cell} className="px-3 py-2">{cell}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-t border-slate-200 dark:border-slate-800">
                    <td className="px-3 py-2">{user.username}</td>
                    <td className="px-3 py-2">{user.email || '—'}</td>
                    <td className="px-3 py-2">
                      <select
                        value={user.role}
                        disabled={roleMutation.isPending}
                        onChange={(event) =>
                          roleMutation.mutate({
                            id: user.id,
                            role: event.target.value as ApiUser['role'],
                          })
                        }
                        aria-label={`Role for ${user.username}`}
                        className="rounded border border-slate-300 bg-transparent px-2 py-1 dark:border-slate-700"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="analyst">Analyst</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState
              title="No application users"
              description="No users are available to manage."
            />
          )}
        </section>
      )}
    </div>
  );
};

function CrawlRunTable({ runs }: { runs: ApiCrawlRun[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-[#111827]">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="bg-slate-50 dark:bg-[#0e1422]">
            {['Source', 'Status', 'Started', 'Articles', 'Duplicates', 'Errors'].map(
              (heading) => (
                <th key={heading} className="px-3 py-2">{heading}</th>
              ),
            )}
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className="border-t border-slate-200 dark:border-slate-800">
              <td className="px-3 py-2">{run.source_name || 'Removed source'}</td>
              <td className="px-3 py-2 capitalize">{run.status}</td>
              <td className="px-3 py-2">
                {run.started_at ? new Date(run.started_at).toLocaleString() : 'Not started'}
              </td>
              <td className="px-3 py-2">{run.articles_created}</td>
              <td className="px-3 py-2">{run.articles_duplicates}</td>
              <td className="max-w-sm px-3 py-2 text-rose-600">{run.error_message || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
