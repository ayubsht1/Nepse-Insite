import React, { useState, useEffect } from 'react';
import { ManagedCompany } from '../../types';
import { X, Building2, Check, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

interface CompanyFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (company: Partial<ManagedCompany>) => void;
  initialCompany?: ManagedCompany | null;
}

const SECTORS = [
  'Commercial Bank',
  'Hydropower',
  'Manufacturing & Processing',
  'Investment',
  'Non-Life Insurance',
  'Life Insurance',
  'Microfinance',
  'Hotels & Tourism',
  'Others / Telecom',
];

export const CompanyFormModal: React.FC<CompanyFormModalProps> = ({
  isOpen,
  onClose,
  onSave,
  initialCompany,
}) => {
  const isEditing = !!initialCompany;

  const [symbol, setSymbol] = useState('');
  const [name, setName] = useState('');
  const [sector, setSector] = useState(SECTORS[0]);
  const [price, setPrice] = useState('100.0');
  const [volume, setVolume] = useState('50000');
  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    if (initialCompany) {
      setSymbol(initialCompany.symbol);
      setName(initialCompany.name);
      setSector(initialCompany.sector);
      setPrice(initialCompany.price.toString());
      setVolume(initialCompany.volume.toString());
    } else {
      setSymbol('');
      setName('');
      setSector(SECTORS[0]);
      setPrice('100.0');
      setVolume('50000');
    }
    setErrors({});
  }, [initialCompany, isOpen]);

  if (!isOpen) return null;

  const validate = () => {
    const newErrors: { [key: string]: string } = {};
    if (!symbol.trim() || symbol.trim().length < 2) {
      newErrors.symbol = 'Symbol must be at least 2 characters.';
    }
    if (!name.trim()) {
      newErrors.name = 'Company legal name is required.';
    }
    const numPrice = parseFloat(price);
    if (isNaN(numPrice) || numPrice <= 0) {
      newErrors.price = 'Price must be a positive number.';
    }
    const numVol = parseInt(volume, 10);
    if (isNaN(numVol) || numVol < 0) {
      newErrors.volume = 'Volume must be a non-negative number.';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const numPrice = parseFloat(price);
    const numVol = parseInt(volume, 10);

    onSave({
      id: initialCompany ? initialCompany.id : symbol.toLowerCase(),
      symbol: symbol.trim().toUpperCase(),
      name: name.trim(),
      sector,
      price: numPrice,
      volume: numVol,
      turnover: numPrice * numVol,
      vwap: numPrice * 0.99,
      change: initialCompany ? initialCompany.change : 0,
      changePercent: initialCompany ? initialCompany.changePercent : 0,
      isActive: initialCompany ? initialCompany.isActive : true,
      isInWatchlist: initialCompany ? initialCompany.isInWatchlist : true,
    });

    toast.success(isEditing ? 'Company Updated' : 'Company Added to Tracked Directory', {
      description: `${symbol.toUpperCase()} details saved successfully.`,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 dark:bg-black/80 backdrop-blur-xs animate-in fade-in duration-150">
      <div
        className="w-full max-w-lg bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#151d30] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              {isEditing ? `Edit Company Details: ${initialCompany.symbol}` : 'Add Tracked NEPSE Company'}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-slate-700 dark:text-slate-300 font-medium block mb-1">
                NEPSE Symbol <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={symbol}
                disabled={isEditing}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="e.g. NABIL"
                className="w-full bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-200 font-mono uppercase focus:outline-none focus:border-slate-400 dark:focus:border-slate-700 disabled:opacity-50"
              />
              {errors.symbol && <p className="text-rose-500 text-[10px] mt-1">{errors.symbol}</p>}
            </div>

            <div>
              <label className="text-slate-700 dark:text-slate-300 font-medium block mb-1">Sector</label>
              <select
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                className="w-full bg-slate-50 dark:bg-[#0e1422] text-slate-900 dark:text-slate-200 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-slate-400 dark:focus:border-slate-700"
              >
                {SECTORS.map((sec) => (
                  <option key={sec} value={sec}>
                    {sec}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="text-slate-700 dark:text-slate-300 font-medium block mb-1">
              Legal Company Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Nabil Bank Limited"
              className="w-full bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-200 focus:outline-none focus:border-slate-400 dark:focus:border-slate-700"
            />
            {errors.name && <p className="text-rose-500 text-[10px] mt-1">{errors.name}</p>}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-slate-700 dark:text-slate-300 font-medium block mb-1">
                Closing Price (LTP in NPR)
              </label>
              <input
                type="number"
                step="0.1"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-200 font-mono focus:outline-none focus:border-slate-400 dark:focus:border-slate-700"
              />
              {errors.price && <p className="text-rose-500 text-[10px] mt-1">{errors.price}</p>}
            </div>

            <div>
              <label className="text-slate-700 dark:text-slate-300 font-medium block mb-1">
                Base Trading Volume (Shares)
              </label>
              <input
                type="number"
                value={volume}
                onChange={(e) => setVolume(e.target.value)}
                className="w-full bg-slate-50 dark:bg-[#0e1422] border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-200 font-mono focus:outline-none focus:border-slate-400 dark:focus:border-slate-700"
              />
              {errors.volume && <p className="text-rose-500 text-[10px] mt-1">{errors.volume}</p>}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Check className="w-3.5 h-3.5" />
              <span>{isEditing ? 'Save Changes' : 'Add Company'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
