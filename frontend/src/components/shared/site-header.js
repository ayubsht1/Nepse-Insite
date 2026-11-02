import Link from "next/link";
import { siteConfig } from "@/config/site";
import { ThemeToggle } from "@/components/shared/theme-toggle";

export function SiteHeader() {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
        <Link className="font-semibold tracking-tight" href="/">
          {siteConfig.name}
        </Link>
        <ThemeToggle />
      </div>
    </header>
  );
}
