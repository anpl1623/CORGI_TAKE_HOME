/* eslint-disable @next/next/no-page-custom-font */
import type { Metadata } from "next";
import "./globals.css";
import Masthead from "@/components/Masthead";
import { metrics } from "@/lib/data";

export const metadata: Metadata = {
  title: "CLM-2026 · Security-deposit claim payout engine",
  description: "Reverse-engineered SDRP claim adjudication: payout lookup, evals, rule book, data findings.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@400..700&family=Archivo:wght@100..900&family=Roboto+Mono:wght@100..700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="sheet">
          <Masthead />
          <main>{children}</main>
          <footer className="pad" style={{ padding: "0.9rem clamp(1.05rem,3.5vw,3rem) 2.5rem", borderTop: "2.5px solid var(--color-ink)" }}>
            <span className="mono" style={{ fontSize: 11, letterSpacing: "0.1em", color: "var(--color-ink-3)" }}>
              CLM-2026 · Andrew Pleeter · {metrics.claims_total.toLocaleString()} claims · {metrics.extracted} extracted · data as of{" "}
              {metrics.generated}
            </span>
          </footer>
        </div>
      </body>
    </html>
  );
}
