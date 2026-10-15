import fs from "node:fs";
import path from "node:path";
import summaryJson from "@data/summary.json";
import metricsJson from "@data/metrics.json";

export type Row = {
  t: number; status: string; actual: number | null; payout: number; verdict: string; basis: string | null;
  decline: string | null; era: string; pm: string | null; family: string; treaty: string | null; date: string;
  max: number | null; ceiling: number | null; conf: number | null; flags: string[]; termination: string | null;
  source: string | null; docs: boolean; heldout: boolean;
};

export type Group = {
  n: number; exact_pct: number; within_5pct_pct: number; within_15pct_pct: number; mape_pct: number | null;
  median_ape_pct: number | null; mae: number | null; decline_accuracy_pct: number | null; declines: number;
  dollar_total_pred: number; dollar_total_truth: number;
};

export type Metrics = {
  generated: string; engine_ms_all_claims: number; claims_total: number; extracted: number;
  groups: Record<string, Group>; ablation: Record<string, Group>;
  declines: { tp: number; fp: number; fn: number; tn: number; precision: number; recall: number };
  error_hist: { bin: string; n: number }[];
  scatter: { t: number; actual: number; payout: number; verdict: string }[];
};

export type Line = { description: string | null; category: string | null; amount: number; paid: number; decision?: string; reason?: string };

export type Detail = {
  tracking: number; era: string; pm_family: string; rent: number | null; ceiling: number | null; ceiling_source: string;
  decline_reason: string | null; lines: Line[]; credits: { description: string; amount: number; type: string }[];
  review_flags: string[]; basis: string | null; mode: string; note: string | null; payout: number; confidence: number | null;
  eligible?: number; credit_total?: number; net_eligible?: number; amount_if_not_declined?: number; comment_basis?: string;
  address: string | null; city: string | null; state: string | null; pm: string | null; status: string; actual: number | null;
  verdict: string; max_benefit: number | null; claim_date: string; lease_start: string; lease_end: string; move_out: string;
  termination: string | null; source: string | null; pre_decline_amount: number | null; docs_only_payout: number;
};

export const summary = summaryJson as Row[];
export const metrics = metricsJson as unknown as Metrics;
export const byId = new Map(summary.map((r) => [r.t, r]));

export function loadDetail(t: number): Detail | null {
  const p = path.join(process.cwd(), "data", "claims", `${t}.json`);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8")) as Detail;
}

/** "49" | "7-20" | "7-20, 49, 100" | "all" | "open" -> tracking numbers present in the book. */
export function parseSelection(spec: string): number[] {
  const s = spec.trim().toLowerCase();
  if (!s) return [];
  if (s === "all") return summary.map((r) => r.t);
  if (s === "open") return summary.filter((r) => r.verdict === "open" && r.status !== "Test Claim").map((r) => r.t);
  const out = new Set<number>();
  for (const part of s.split(/[,\s]+/)) {
    const m = part.match(/^(\d+)\s*[-–]\s*(\d+)$/);
    if (m) {
      const [a, b] = [Number(m[1]), Number(m[2])].sort((x, y) => x - y);
      for (let i = a; i <= Math.min(b, a + 2000); i++) out.add(i);
    } else if (/^\d+$/.test(part)) out.add(Number(part));
  }
  return [...out].filter((t) => byId.has(t)).sort((a, b) => a - b);
}

export const money = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export const money0 = (v: number | null | undefined) =>
  v === null || v === undefined ? "—" : `$${Math.round(v).toLocaleString("en-US")}`;
export const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v.toFixed(1)}%`);

export function summarize(rows: Row[]) {
  const scored = rows.filter((r) => r.verdict !== "open" && r.actual !== null && r.status !== "Test Claim");
  const exact = scored.filter((r) => r.verdict === "exact").length;
  const paid = scored.filter((r) => (r.actual ?? 0) > 0);
  const mape = paid.length ? (100 * paid.reduce((s, r) => s + Math.abs(r.payout - (r.actual ?? 0)) / (r.actual ?? 1), 0)) / paid.length : null;
  return {
    n: scored.length, exact, exactPct: scored.length ? (100 * exact) / scored.length : 0, mape,
    pred: rows.reduce((s, r) => s + r.payout, 0), truth: scored.reduce((s, r) => s + (r.actual ?? 0), 0),
  };
}
