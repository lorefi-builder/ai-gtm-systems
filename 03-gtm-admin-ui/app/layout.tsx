import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  variable: "--font-fraunces",
  display: "swap",
});

const inter = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Activation Labs · GTM Admin",
  description:
    "Human review queue for agent-proposed GTM content. Demo surface for the Lorefi GTM stack.",
};

function PhoenixMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      className={className}
    >
      <path d="M16 4c-3 4-2 7 0 10 2-3 3-6 0-10z" fill="currentColor" />
      <path
        d="M8 12c2 0 4 1 5 3-2 1-5 1-7-1l2-2z"
        fill="currentColor"
        opacity="0.85"
      />
      <path
        d="M24 12c-2 0-4 1-5 3 2 1 5 1 7-1l-2-2z"
        fill="currentColor"
        opacity="0.85"
      />
      <path
        d="M16 14c-2 3-2 7 0 12 2-5 2-9 0-12z"
        fill="currentColor"
        opacity="0.95"
      />
      <path
        d="M11 20c1 2 3 4 5 6 2-2 4-4 5-6-3 1-7 1-10 0z"
        fill="currentColor"
        opacity="0.7"
      />
    </svg>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${inter.variable} ${plexMono.variable}`}
    >
      <body className="min-h-screen bg-[var(--al-cream)] text-[var(--al-ink)]">
        <div
          aria-hidden
          className="pointer-events-none fixed inset-0 bg-al-grid bg-[length:48px_48px]"
        />

        <header
          className="sticky top-0 z-30 border-b bg-[var(--al-ink)] text-[var(--al-sand)]"
          style={{ borderBottomColor: "var(--al-stroke-gold)" }}
        >
          <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
            <div className="flex items-center gap-2.5">
              <span className="text-[var(--al-gold)]">
                <PhoenixMark className="h-4 w-4" />
              </span>
              <span className="font-serif text-[18px] font-semibold leading-none text-[var(--al-sand)]">
                Activation Labs
                <span className="text-[var(--al-sand-mute)]">
                  {" "}
                  · GTM Admin
                </span>
              </span>
            </div>

            <div className="inline-flex items-center gap-1.5 rounded-full bg-[var(--al-red)] px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-[var(--al-cream)]">
              <svg
                viewBox="0 0 12 12"
                fill="none"
                aria-hidden
                className="h-3 w-3"
              >
                <rect
                  x="3"
                  y="6"
                  width="6"
                  height="4"
                  rx="0.5"
                  stroke="currentColor"
                  strokeWidth="1"
                />
                <path
                  d="M4.5 6V4a1.5 1.5 0 013 0v2"
                  stroke="currentColor"
                  strokeWidth="1"
                />
              </svg>
              <span>Demo · Fictional Lorefi Data</span>
            </div>
          </div>
        </header>

        <main className="relative">{children}</main>
      </body>
    </html>
  );
}
