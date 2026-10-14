import "./globals.css";
import type { Metadata, Viewport } from "next";
import Link from "next/link";
import NavAuth from "@/components/NavAuth";
import { AiNotice, LanguageSelect, SiteFooter, SkipLink } from "@/components/SiteChrome";

export const metadata: Metadata = {
  title: "Face Search",
  description:
    "AI facial-recognition search over a private, consented photo collection. Results are reviewed by a human before release.",
};

// Works on phones and tablets; pinch-zoom stays enabled for low-vision users.
export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <SkipLink />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-8 pb-24">
          <header className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <Link href="/" className="flex items-center gap-3 group">
              <div aria-hidden className="w-9 h-9 rounded-xl bg-gradient-to-tr from-accent to-accent2 shadow-lg shadow-accent/30" />
              <div className="leading-tight">
                <div className="font-semibold tracking-tight">Face Search</div>
                <div className="text-xs text-slate-300">InsightFace + Qdrant · local-first</div>
              </div>
            </Link>
            <div className="flex flex-wrap items-center gap-3">
              <LanguageSelect />
              <NavAuth />
            </div>
          </header>
          <AiNotice />
          <main id="main" tabIndex={-1}>
            {children}
          </main>
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
