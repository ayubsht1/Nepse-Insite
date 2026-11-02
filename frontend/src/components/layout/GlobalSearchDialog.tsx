'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useApp } from '../../context/AppContext';
import { fetchCompanies } from '../../services/api';
import { Building2, Search, X, ArrowRight } from 'lucide-react';

export const GlobalSearchDialog: React.FC = () => {
  const {
    isSearchOpen,
    setIsSearchOpen,
    setSelectedCompanyId,
    setActiveTab,
  } = useApp();
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const companiesQuery = useQuery({
    queryKey: ['companies-search', query],
    queryFn: () => fetchCompanies({ search: query || undefined }),
    enabled: isSearchOpen,
  });
  const companies = companiesQuery.data?.results ?? [];

  useEffect(() => {
    if (isSearchOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isSearchOpen]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isSearchOpen) setIsSearchOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSearchOpen, setIsSearchOpen]);

  if (!isSearchOpen) return null;

  const handleSelect = (symbol: string) => {
    setSelectedCompanyId(symbol.toLowerCase());
    setActiveTab('companies');
    setIsSearchOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/75 px-4 pt-16 backdrop-blur-sm sm:pt-24">
      <div
        className="w-full max-w-2xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700/80 dark:bg-[#111827]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center border-b border-slate-200 bg-slate-50 px-4 py-3.5 dark:border-slate-800 dark:bg-[#151d30]">
          <Search className="h-5 w-5 shrink-0 text-slate-400" />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search companies by symbol, name, or sector"
            className="w-full border-0 bg-transparent px-3 text-sm text-slate-900 placeholder-slate-400 focus:outline-none dark:text-slate-100"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              aria-label="Clear search"
              className="p-1 text-slate-400"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className="max-h-96 overflow-y-auto p-2">
          <div className="flex justify-between px-3 py-1.5 text-[11px] uppercase tracking-wider text-slate-500">
            <span>{query ? 'Matching companies' : 'Company directory'}</span>
            <span>
              {companiesQuery.data?.count ?? 0} records
            </span>
          </div>
          {companiesQuery.isLoading ? (
            <p className="p-8 text-center text-sm text-slate-500">Loading companies…</p>
          ) : companiesQuery.isError ? (
            <p role="alert" className="p-8 text-center text-sm text-rose-600">
              {companiesQuery.error.message}
            </p>
          ) : companies.length ? (
            companies.map((company) => (
              <button
                key={company.id}
                onClick={() => handleSelect(company.symbol)}
                className="group flex w-full items-center justify-between gap-3 rounded-lg p-3 text-left hover:bg-slate-100 dark:hover:bg-slate-800/60"
              >
                <span className="flex min-w-0 items-center gap-3">
                  <span className="flex h-10 w-12 shrink-0 items-center justify-center rounded border border-slate-200 bg-slate-100 font-mono text-xs font-bold text-emerald-600 dark:border-slate-800 dark:bg-[#0b0f19] dark:text-emerald-400">
                    {company.symbol}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold">
                      {company.name}
                    </span>
                    <span className="block truncate text-xs text-slate-500">
                      {company.sector || 'Sector unavailable'}
                    </span>
                  </span>
                </span>
                <ArrowRight className="h-4 w-4 shrink-0 text-slate-400 group-hover:text-emerald-600" />
              </button>
            ))
          ) : (
            <div className="py-12 text-center">
              <Building2 className="mx-auto mb-2 h-8 w-8 text-slate-400" />
              <p className="text-sm">No matching company records.</p>
            </div>
          )}
        </div>
        <div className="border-t border-slate-200 bg-slate-50 px-4 py-2.5 text-[11px] text-slate-500 dark:border-slate-800 dark:bg-[#0b0f19]">
          Search results come from the backend company directory.
        </div>
      </div>
    </div>
  );
};
