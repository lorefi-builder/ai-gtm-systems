import type { Metadata } from "next";
import { DM_Serif_Display, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

const serif = DM_Serif_Display({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-serif",
  display: "swap",
});

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-sans",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Activation Labs · GTM Admin",
  description:
    "Human review queue for agent-proposed GTM content. Demo surface for the Lorefi GTM stack.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${serif.variable} ${sans.variable} ${mono.variable} dark`}
    >
      <body className="min-h-screen bg-teal-deep text-sand">
        <div className="pointer-events-none fixed inset-0 bg-grid bg-[length:48px_48px] opacity-60" />

        <header className="sticky top-0 z-30 border-b border-sand/10 bg-teal-deep/85 backdrop-blur supports-[backdrop-filter]:bg-teal-deep/70">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-baseline gap-2">
              <span className="font-serif text-xl text-sand">
                Activation Labs
              </span>
              <span className="font-mono text-xs uppercase tracking-[0.18em] text-sand-muted">
                · GTM Admin
              </span>
            </div>
            <div className="rounded-full border border-coral/40 bg-coral/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-coral">
              DEMO — Fictional Lorefi data. Real pattern.
            </div>
          </div>
        </header>

        <main className="relative mx-auto max-w-6xl px-6 py-10">
          {children}
        </main>
      </body>
    </html>
  );
}
