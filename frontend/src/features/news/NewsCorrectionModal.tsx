import React, { useState } from 'react';
import { MarketNewsItem, NewsTagCorrection } from '../../types';
import { useApp } from '../../context/AppContext';
import { MOCK_COMPANIES } from '../../data/mockData';
import { StatusBadge } from '../../components/ui';
import {
  Tag,
  X,
  Plus,
  AlertCircle,
  CheckCircle2,
  Shield,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { toast } from 'sonner';

interface NewsCorrectionModalProps {
  article: MarketNewsItem;
  isOpen: boolean;
  onClose: () => void;
  onSaveCorrection: (
    articleId: string,
    correctedTags: string[],
    correctedCategory: MarketNewsItem['category'],
    log: NewsTagCorrection
  ) => void;
}

const CATEGORIES: MarketNewsItem['category'][] = [
  'Earnings',
  'Policy',
  'Dividend',
  'Hydropower',
  'Listing',
  'Banking',
  'Economy',
];

export const NewsCorrectionModal: React.FC<NewsCorrectionModalProps> = ({
  article,
  isOpen,
  onClose,
  onSaveCorrection,
}) => {
  const { userProfile, userRole } = useApp();
  const canEdit = userRole === 'admin' || userRole === 'analyst';

  // Form states
  const [selectedCategory, setSelectedCategory] = useState<MarketNewsItem['category']>(article.category);
  const [tags, setTags] = useState<string[]>([...article.relatedCompanies]);
  const [newTickerInput, setNewTickerInput] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [isConfirming, setIsConfirming] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleAddTag = (ticker: string) => {
    const cleanTicker = ticker.trim().toUpperCase();
    if (!cleanTicker) return;
    if (!tags.includes(cleanTicker)) {
      setTags([...tags, cleanTicker]);
    }
    setNewTickerInput('');
  };

  const handleRemoveTag = (tickerToRemove: string) => {
    setTags(tags.filter((t) => t !== tickerToRemove));
  };

  const handleSave = () => {
    if (tags.length === 0) {
      toast.error('At least one company tag is required.');
      return;
    }

    const logEntry: NewsTagCorrection = {
      id: `corr-${Date.now()}`,
      articleId: article.id,
      articleTitle: article.headline,
      analystName: userProfile.name,
      analystRole: userRole,
      timestamp: 'Just now',
      previousTags: [...article.relatedCompanies],
      correctedTags: [...tags],
      previousCategory: article.category,
      correctedCategory: selectedCategory,
      reason: reason.trim() || 'Manual entity tag correction by market intelligence analyst.',
    };

    onSaveCorrection(article.id, tags, selectedCategory, logEntry);
    toast.success('Tags Corrected Successfully', {
      description: `Updated associations for "${article.headline.slice(0, 40)}..."`,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 dark:bg-black/80 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#151d30] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Tag className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              News Categorization & Entity Tag Correction
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Permission Check Notice */}
          {!canEdit && (
            <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 flex items-start gap-2.5 text-rose-800 dark:text-rose-300">
              <Shield className="w-4 h-4 shrink-0 mt-0.5 text-rose-500 dark:text-rose-400" />
              <div>
                <p className="font-semibold">Read-Only Mode (Viewer)</p>
                <p className="text-[11px] text-rose-600 dark:text-rose-400/90 mt-0.5">
                  Only users with Analyst or Administrator privileges can modify automated NLP tags and classifications. Switch your role in the top-right profile dropdown to test corrections.
                </p>
              </div>
            </div>
          )}

          {/* Article Summary Lockup */}
          <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800/80 space-y-1.5">
            <div className="flex items-center gap-2 text-[11px]">
              <span className="font-mono text-slate-500 dark:text-slate-400">{article.source}</span>
              <span className="text-slate-400 dark:text-slate-600">·</span>
              <span className="text-slate-500 dark:text-slate-400">{article.publishedAt}</span>
              <span className="text-slate-400 dark:text-slate-600">·</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400 font-medium">
                Confidence: {Math.round(article.confidence * 100)}%
              </span>
            </div>
            <p className="font-semibold text-slate-900 dark:text-slate-200 text-xs leading-snug">
              {article.headline}
            </p>
          </div>

          {/* Category Selector */}
          <div>
            <label className="font-medium text-slate-700 dark:text-slate-300 block mb-1.5">
              Financial Topic Classification
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  disabled={!canEdit}
                  onClick={() => setSelectedCategory(cat)}
                  className={`p-2 rounded-lg border text-left font-mono text-xs transition-colors ${
                    selectedCategory === cat
                      ? 'bg-purple-50 dark:bg-purple-950/60 border-purple-400 dark:border-purple-500 text-purple-700 dark:text-purple-300 font-semibold'
                      : 'bg-white dark:bg-[#0e1422] border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Related Company Tags Editor */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="font-medium text-slate-700 dark:text-slate-300">
                Associated NEPSE Listed Companies
              </label>
              <span className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                {tags.length} linked tickers
              </span>
            </div>

            {/* Current Active Tags */}
            <div className="p-3 rounded-lg bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 flex flex-wrap gap-2 min-h-[46px] items-center">
              {tags.length === 0 ? (
                <span className="text-slate-500 italic">No company associations selected</span>
              ) : (
                tags.map((ticker) => (
                  <span
                    key={ticker}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-100 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-800/80 text-emerald-800 dark:text-emerald-400 font-mono font-bold text-xs"
                  >
                    <span>{ticker}</span>
                    {canEdit && (
                      <button
                        onClick={() => handleRemoveTag(ticker)}
                        className="hover:text-rose-600 dark:hover:text-rose-400 ml-0.5"
                        title={`Remove ${ticker}`}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </span>
                ))
              )}
            </div>

            {/* Quick Add Ticker Suggestions & Custom Input */}
            {canEdit && (
              <div className="mt-2 space-y-2">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={newTickerInput}
                    onChange={(e) => setNewTickerInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddTag(newTickerInput);
                      }
                    }}
                    placeholder="Enter ticker (e.g. NABIL, CIT)..."
                    className="flex-1 bg-white dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-200 font-mono uppercase focus:outline-none focus:border-slate-400 dark:focus:border-slate-700 shadow-2xs"
                  />
                  <button
                    onClick={() => handleAddTag(newTickerInput)}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-semibold flex items-center gap-1 border border-slate-200 dark:border-transparent transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add</span>
                  </button>
                </div>

                <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                  <span>Quick Add:</span>
                  {MOCK_COMPANIES.slice(0, 7).map((c) => (
                    <button
                      key={c.id}
                      onClick={() => handleAddTag(c.symbol)}
                      disabled={tags.includes(c.symbol)}
                      className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800/80 hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed font-mono text-[10px] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-transparent transition-colors"
                    >
                      +{c.symbol}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Justification / Reason */}
          {canEdit && (
            <div>
              <label className="font-medium text-slate-700 dark:text-slate-300 block mb-1">
                Correction Justification & Audit Note
              </label>
              <textarea
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explain why this tag or category was modified (e.g., False positive mention in article body)..."
                className="w-full bg-white dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg p-2.5 text-xs text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-slate-400 dark:focus:border-slate-700"
              />
            </div>
          )}

          {/* Change Comparison Preview (Previous vs Corrected) */}
          <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5 font-mono text-[11px]">
            <span className="text-slate-700 dark:text-slate-400 font-sans font-semibold block mb-1">
              Audit Delta Comparison:
            </span>
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
              <span>Category:</span>
              <div className="flex items-center gap-2">
                <span className="text-slate-400 dark:text-slate-500 line-through">{article.category}</span>
                <ArrowRight className="w-3 h-3 text-slate-400 dark:text-slate-600" />
                <span className="text-purple-600 dark:text-purple-400 font-semibold">{selectedCategory}</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
              <span>Company Tickers:</span>
              <div className="flex items-center gap-2">
                <span className="text-slate-400 dark:text-slate-500">[{article.relatedCompanies.join(', ') || 'None'}]</span>
                <ArrowRight className="w-3 h-3 text-slate-400 dark:text-slate-600" />
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">[{tags.join(', ') || 'None'}]</span>
              </div>
            </div>
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-800/80">
              <span>Auditor:</span>
              <span className="text-slate-900 dark:text-slate-200 font-sans">
                {userProfile.name} ({userRole.toUpperCase()})
              </span>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3.5 px-5 bg-slate-50 dark:bg-[#0e1422] border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
          >
            Cancel
          </button>

          {canEdit ? (
            isConfirming ? (
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-amber-600 dark:text-amber-400 font-medium">Confirm audit write?</span>
                <button
                  onClick={handleSave}
                  className="px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors flex items-center gap-1 shadow-xs"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Yes, Save Correction</span>
                </button>
                <button
                  onClick={() => setIsConfirming(false)}
                  className="px-2 py-1.5 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white"
                >
                  Back
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsConfirming(true)}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 rounded-lg shadow-xs transition-colors flex items-center gap-1.5"
              >
                <span>Review & Save</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )
          ) : (
            <span className="text-xs text-slate-500">View-only mode</span>
          )}
        </div>
      </div>
    </div>
  );
};
