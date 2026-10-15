"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/lookup", label: "Payout lookup" },
  { href: "/evals", label: "Evals" },
  { href: "/rules", label: "Rule book" },
  { href: "/findings", label: "Data findings" },
  { href: "/system", label: "System" },
];

export default function Masthead() {
  const path = usePathname();
  return (
    <header className="mast">
      <div className="mast__in pad">
        <Link href="/" className="mast__name">
          CLM-2026
        </Link>
        <nav className="mast__nav" aria-label="Sections" style={{ overflowX: "auto" }}>
          {NAV.map((n) => {
            const active = n.href === "/" ? path === "/" : path.startsWith(n.href) || (n.href === "/lookup" && path.startsWith("/claim"));
            return (
              <Link key={n.href} href={n.href} className="mast__link" aria-current={active ? "page" : undefined}>
                {n.label}
              </Link>
            );
          })}
        </nav>
        <span className="mast__doc hidden md:inline">
          Corgi · work trial · <b>rev A</b>
        </span>
      </div>
    </header>
  );
}
