import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Òfin — understand Nigeria's National Assembly",
  description:
    "Search any issue. Find the bills behind it. Get a plain-language explanation, verified against the original document.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="mx-auto flex max-w-2xl items-center justify-between border-b border-border px-5 py-4">
          <Link href="/" className="text-xl font-bold no-underline">
            Òfin
          </Link>
          <nav>
            <Link href="/activity" className="text-sm text-muted no-underline">
              Activity
            </Link>
          </nav>
        </header>
        <main className="mx-auto min-h-[70vh] max-w-2xl px-5 py-5">{children}</main>
        <footer className="mx-auto max-w-2xl border-t border-border px-5 py-6 pb-12 text-xs text-muted">
          <p>
            Full-text explanations cover bills from 2016–2021. Activity covers 2025–2026.
            These two layers barely overlap.
          </p>
        </footer>
      </body>
    </html>
  );
}
