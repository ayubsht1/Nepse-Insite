import { AppProviders } from "@/providers/app-providers";
import { SiteHeader } from "@/components/shared/site-header";
import { siteConfig } from "@/config/site";
import "./globals.css";

export const metadata = {
  title: siteConfig.name,
  description: siteConfig.description,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <AppProviders>
          <div className="flex min-h-screen flex-col">
            <SiteHeader />
            <main className="mx-auto flex w-full max-w-6xl flex-1 items-center px-6 py-16">
              {children}
            </main>
          </div>
        </AppProviders>
      </body>
    </html>
  );
}
