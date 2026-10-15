import Link from "next/link";
import { Search } from "lucide-react";

const EXAMPLES = ["49", "7-20", "593", "764", "1168", "open"];

export default function LookupBar({ value = "" }: { value?: string }) {
  return (
    <div>
      <form action="/lookup" method="get" className="look" role="search">
        <label htmlFor="q" className="sr-only">
          Tracking number or range
        </label>
        <input id="q" name="q" defaultValue={value} placeholder="Tracking number, range or list: 49 · 7-20 · 7-20,49 · open · all" autoComplete="off" />
        <button className="btn" type="submit">
          <Search size={14} aria-hidden /> Compute payout
        </button>
      </form>
      <div className="look__ex">
        <span className="small mono">Try</span>
        {EXAMPLES.map((e) => (
          <Link key={e} href={`/lookup?q=${encodeURIComponent(e)}`} className="chip">
            {e}
          </Link>
        ))}
      </div>
    </div>
  );
}
