import "./globals.css";
import type { Metadata, Viewport } from "next";
import SiteHeader from "@/components/SiteHeader";
import { AiNotice, SiteFooter, SkipLink } from "@/components/SiteChrome";

export const metadata: Metadata = {
  title: "Face Search",
  description:
    "AI facial-recognition search over a private, consented photo collection. Results are reviewed by a human before release.",
};

// Works on phones and tablets; pinch-zoom stays enabled for low-vision users.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#13161d" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col font-sans antialiased">
        <SkipLink />
        <SiteHeader />
        <div className="mx-auto w-full max-w-6xl flex-1 px-4 pt-6 sm:px-6 sm:pt-8">
          <AiNotice />
          <main id="main" tabIndex={-1} className="focus:outline-none">
            {children}
          </main>
        </div>
        <SiteFooter />
      </body>
    </html>
  );
}
