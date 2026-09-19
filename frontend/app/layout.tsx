import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Face Search",
  description: "Find every photo someone appears in.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <div className="max-w-6xl mx-auto px-6 pt-8 pb-24">
          <header className="flex items-center justify-between mb-10">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-accent to-accent2 shadow-lg shadow-accent/30" />
              <div className="leading-tight">
                <div className="font-semibold tracking-tight">Face Search</div>
                <div className="text-xs text-slate-400">
                  InsightFace + Qdrant · local-first
                </div>
              </div>
            </Link>
            <nav className="flex items-center gap-2 text-sm">
              <Link className="btn-ghost" href="/">Index</Link>
              <Link className="btn-ghost" href="/search">Search</Link>
              <Link className="btn-ghost" href="/gallery">Gallery</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
