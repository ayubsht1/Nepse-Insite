import type { Metadata } from 'next';
import Script from 'next/script';
import type { ReactNode } from 'react';
import './globals.css';

const description =
  'Real-time NEPSE stock market analytics, financial news intelligence, VWAP broker breakdowns, and cross-company comparisons.';

export const metadata: Metadata = {
  title: 'NEPSE Insight - Nepal Stock Market Analytics',
  description,
  openGraph: {
    title: 'NEPSE Insight - Nepal Stock Market Analytics',
    description,
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <Script id="theme-preference" strategy="beforeInteractive">
          {`try {
            const theme = window.localStorage.getItem('nepse_insight_theme');
            document.documentElement.classList.toggle('dark', theme !== 'light');
          } catch {
            document.documentElement.classList.add('dark');
          }`}
        </Script>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-slate-50 text-slate-900 dark:bg-[#0B0F19] dark:text-slate-100 antialiased selection:bg-emerald-500/20 selection:text-emerald-300 transition-colors duration-200">
        {children}
      </body>
    </html>
  );
}
