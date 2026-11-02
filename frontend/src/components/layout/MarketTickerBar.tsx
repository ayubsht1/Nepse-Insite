import React from 'react';
import { Info } from 'lucide-react';

export const MarketTickerBar: React.FC = () => (
  <div className="w-full border-b border-slate-200 bg-slate-100 px-4 py-2 text-xs text-slate-500 transition-colors dark:border-slate-800/80 dark:bg-[#0e1422] dark:text-slate-400">
    <div className="flex items-center gap-2">
      <Info className="h-3.5 w-3.5 shrink-0" />
      <span>
        Live NEPSE indices are unavailable: no verified index data source is
        configured.
      </span>
    </div>
  </div>
);
