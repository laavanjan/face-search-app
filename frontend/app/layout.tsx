import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";
import NavAuth from "@/components/NavAuth";

export const metadata: Metadata = {
  title: "Face Search",
  description:
    "AI facial-recognition search over a private, consented photo collection. Results are reviewed by a human before release.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <div className="max-w-6xl mx-auto px-6 pt-8 pb-24">
          <header className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-accent to-accent2 shadow-lg shadow-accent/30" />
              <div className="leading-tight">
                <div className="font-semibold tracking-tight">Face Search</div>
                <div className="text-xs text-slate-400">
                  InsightFace + Qdrant · local-first
                </div>
              </div>
            </Link>
            <NavAuth />
          </header>
          <div
            role="note"
            className="mb-8 rounded-xl border border-amber-300/20 bg-amber-300/5 px-4 py-2 text-xs text-amber-100/90"
          >
            <strong>AI system:</strong> this is an automated facial-recognition tool. Uploaded photos are
            analysed to detect faces and create biometric embeddings; matches are AI similarity
            estimates that can be wrong and are released only after human review.{" "}
            <Link href="/privacy" className="underline">Privacy &amp; AI use</Link> ·{" "}
            <Link href="/appeal" className="underline">Challenge a result</Link>
          </div>
          {children}
        </div>
      </body>
    </html>
  );
}
