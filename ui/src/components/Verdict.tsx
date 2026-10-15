import { Check, CircleDot, X, Minus } from "lucide-react";

const LABEL: Record<string, string> = { exact: "Exact", close: "≤5%", near: "≤15%", miss: "Miss", open: "Open" };

export default function Verdict({ v }: { v: string }) {
  const Icon = v === "exact" ? Check : v === "miss" ? X : v === "open" ? Minus : CircleDot;
  return (
    <span className={`vd vd--${v}`}>
      <Icon size={12} aria-hidden strokeWidth={2.5} />
      {LABEL[v] ?? v}
    </span>
  );
}
