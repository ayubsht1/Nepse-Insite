import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format currency in Nepalese Rupees (NPR)
 * Example: 2450.5 -> "Rs. 2,450.50"
 */
export function formatNPR(value: number, includeDecimals = true): string {
  if (value === undefined || value === null || isNaN(value)) return 'Rs. --';
  const formatted = new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: includeDecimals ? 2 : 0,
    maximumFractionDigits: includeDecimals ? 2 : 0,
  }).format(value);
  return `Rs. ${formatted}`;
}

/**
 * Format large numbers in South Asian denomination (Kharba, Arba, Karod, Lakh)
 */
export function formatLargeAmount(amount: number): string {
  if (amount >= 1e11) {
    return `Rs. ${(amount / 1e11).toFixed(2)} Kharba`;
  } else if (amount >= 1e9) {
    return `Rs. ${(amount / 1e9).toFixed(2)} Arba`;
  } else if (amount >= 1e7) {
    return `Rs. ${(amount / 1e7).toFixed(2)} Cr`;
  } else if (amount >= 1e5) {
    return `Rs. ${(amount / 1e5).toFixed(2)} Lakh`;
  }
  return formatNPR(amount, false);
}

/**
 * Format percentage with positive/negative signs
 */
export function formatPercent(value: number): string {
  if (value === undefined || value === null || isNaN(value)) return '0.00%';
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

/**
 * Format stock volume (shares)
 */
export function formatVolume(volume: number): string {
  if (volume >= 1e6) {
    return `${(volume / 1e6).toFixed(2)}M`;
  } else if (volume >= 1e3) {
    return `${(volume / 1e3).toFixed(1)}K`;
  }
  return volume.toLocaleString('en-IN');
}

/**
 * Get current Nepal Standard Time (UTC + 5:45)
 */
export function getNepalDateTime(): {
  dateEn: string;
  dateBs: string;
  timeNPT: string;
  isMarketOpen: boolean;
} {
  // Current date in UTC
  const now = new Date();
  // NPT is UTC + 5h 45m
  const utcOffset = now.getTime() + now.getTimezoneOffset() * 60000;
  const nptTime = new Date(utcOffset + 3600000 * 5.75);

  const hours = nptTime.getHours();
  const minutes = nptTime.getMinutes();
  const day = nptTime.getDay(); // 0 is Sunday, 5 is Friday

  // NEPSE trading hours: Sunday to Thursday, 11:00 AM to 3:00 PM NPT
  // (In Nepal Friday and Saturday are weekend)
  const isTradingDay = day >= 0 && day <= 4; // Sun=0, Mon=1, Tue=2, Wed=3, Thu=4
  const isTradingHour = (hours > 11 || (hours === 11 && minutes >= 0)) && hours < 15;
  const isMarketOpen = isTradingDay && isTradingHour;

  const timeFormatted = nptTime.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });

  const dateFormatted = nptTime.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  // Approximate Vikram Samvat (BS) year is ~56.7 years ahead
  const bsDate = 'Kartik 16, 2081 BS';

  return {
    dateEn: dateFormatted,
    dateBs: bsDate,
    timeNPT: timeFormatted,
    isMarketOpen,
  };
}
