import React from 'react';
import { MarketNewsItem } from '../../types';
import { useApp } from '../../context/AppContext';
import { StatusBadge } from '../../components/ui';
import {
  X,
  ExternalLink,
  Tag,
  Building2,
  Calendar,
  ShieldCheck,
  CheckCircle2,
  History,
} from 'lucide-react';

interface ArticleDetailModalProps {
  article: MarketNewsItem | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenCorrection: (article: MarketNewsItem) => void;
}

export const ArticleDetailModal: React.FC<ArticleDetailModalProps> = ({
  article,
  isOpen,
  onClose,
  onOpenCorrection,
}) => {
  const { setSelectedCompanyId, setActiveTab, userRole } = useApp();
  const canEdit = userRole === 'admin' || userRole === 'analyst';

  if (!isOpen || !article) return null;

  const handleTickerClick = (symbol: string) => {
    setSelectedCompanyId(symbol.toLowerCase());
    setActiveTab('companies');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 dark:bg-black/80 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#151d30] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
              {article.source}
            </span>
            <span className="text-slate-400 dark:text-slate-600">·</span>
            <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">{article.publishedAt}</span>
          </div>

          <div className="flex items-center gap-2">
            {canEdit && (
              <button
                onClick={() => {
                  onClose();
                  onOpenCorrection(article);
                }}
                className="px-2.5 py-1 text-xs font-semibold text-purple-700 dark:text-purple-300 hover:text-purple-900 dark:hover:text-white bg-purple-50 dark:bg-purple-950/60 hover:bg-purple-100 dark:hover:bg-purple-900/60 border border-purple-200 dark:border-purple-800/60 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <Tag className="w-3.5 h-3.5" />
                <span>Correct Tags</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Article Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-700 dark:text-slate-300">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <StatusBadge label={article.category} variant="purple" />
              <span className="text-[11px] font-mono text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/40 px-2 py-0.5 rounded">
                NLP Confidence: {Math.round(article.confidence * 100)}%
              </span>
              {article.isManuallyCorrected && (
                <span className="text-[11px] font-mono text-sky-700 dark:text-sky-400 bg-sky-50 dark:bg-sky-950/40 border border-sky-200 dark:border-sky-800/40 px-2 py-0.5 rounded flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  Verified
                </span>
              )}
            </div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white tracking-tight leading-snug">
              {article.headline}
            </h2>
          </div>

          {/* Related Company Chips */}
          <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
            <span className="text-slate-500 dark:text-slate-400 text-xs">Associated Equities:</span>
            <div className="flex flex-wrap items-center gap-2">
              {article.relatedCompanies.length === 0 ? (
                <span className="text-slate-400 dark:text-slate-500 italic">No tickers linked</span>
              ) : (
                article.relatedCompanies.map((ticker) => (
                  <button
                    key={ticker}
                    onClick={() => handleTickerClick(ticker)}
                    className="px-2.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-400 font-mono font-bold text-xs hover:bg-emerald-200 dark:hover:bg-emerald-900/60 transition-colors"
                  >
                    {ticker}
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Body Content */}
          <div className="space-y-3 leading-relaxed text-slate-700 dark:text-slate-300 text-xs whitespace-pre-line border-t border-slate-200 dark:border-slate-800/80 pt-4">
            {article.content || article.excerpt}
          </div>

          {/* Article Correction History (Audit Trail) */}
          {article.correctionHistory && article.correctionHistory.length > 0 && (
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 space-y-2 mt-4">
              <div className="flex items-center gap-2 text-slate-900 dark:text-slate-200 font-semibold">
                <History className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                <span>Analyst Tag Correction History</span>
              </div>
              <div className="divide-y divide-slate-200 dark:divide-slate-800 text-[11px] font-mono">
                {article.correctionHistory.map((hist) => (
                  <div key={hist.id} className="py-2 space-y-1">
                    <div className="flex justify-between text-slate-500 dark:text-slate-400">
                      <span>Auditor: {hist.analystName} ({hist.analystRole})</span>
                      <span>{hist.timestamp}</span>
                    </div>
                    <div className="text-slate-800 dark:text-slate-300">
                      Previous: [{hist.previousTags.join(', ')}] ({hist.previousCategory}) → Corrected: [{hist.correctedTags.join(', ')}] ({hist.correctedCategory})
                    </div>
                    {hist.reason && (
                      <p className="text-slate-500 dark:text-slate-400 font-sans italic text-[11px]">
                        "{hist.reason}"
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3.5 px-6 bg-slate-50 dark:bg-[#0e1422] border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs">
          <span className="text-slate-500 dark:text-slate-400">
            Source Publisher: {article.source} News Desk
          </span>

          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 border border-slate-200 dark:border-transparent rounded-lg transition-colors inline-flex items-center gap-1.5 font-medium shadow-2xs"
            >
              <span>Open External Article</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};
