"""Command line: compute payouts for a tracking number, a range, or the whole book.

  python payout.py 49                 # full adjuster-style breakdown
  python payout.py 7-20               # table, compared to the Approved Benefit Amount
  python payout.py 7-20,49 --detail   # breakdown for each
  python payout.py all --summary      # accuracy over every decided claim
  python payout.py 49 --json          # machine-readable decision
"""
import argparse
import json
import sys
import time
from collections import defaultdict

from .engine import build_duplicate_index, compute, load_extraction
from .metrics import bucket, summarize
from .sheet import load_claims, parse_selection


def money(v):
    return "-" if v is None else f"${v:,.2f}"


def detail(claim, d):
    print(f"\n=== Claim {claim.tracking} | {claim.address or ''} | {claim.pm_company or ''}")
    print(f"    claim date {claim.claim_date}  era {d['era']}  rent {money(d['rent'])}  "
          f"Max Benefit {money(claim.max_benefit)}  ceiling {money(d['ceiling'])} ({d['ceiling_source']})")
    if d.get("note"):
        print(f"    adjuster note: {d['note'][:160]}")
    if d.get("decline_reason"):
        print(f"    DECLINE: {d['decline_reason']}  (would have paid {money(d.get('amount_if_not_declined'))})")
    for li in d.get("lines") or []:
        mark = {"covered": "+", "partial": "~", "excluded": "x", "skip": "."}.get(li.get("decision"), "?")
        print(f"    {mark} {money(li['amount']):>12} -> {money(li.get('paid')):>12}  [{li.get('category')}] "
              f"{(li.get('description') or '')[:60]}  ({li.get('reason')})")
    for c in d.get("credits") or []:
        print(f"    - {money(c['amount']):>12}  credit: {c['description']}")
    if d.get("eligible") is not None:
        print(f"    eligible {money(d['eligible'])} - credits {money(d.get('credit_total'))} = {money(d.get('net_eligible'))}")
    print(f"    PAYOUT {money(d['payout'])}  basis: {d.get('basis')}  confidence {d.get('confidence')}"
          + (f"  review: {', '.join(d['review_flags'])}" if d.get("review_flags") else ""))
    truth = claim.truth
    if claim.pre_decline_amount:
        print(f"    note: sheet keeps {money(claim.pre_decline_amount)} calculated before the claim was declined/cancelled (nothing paid)")
    if claim.is_decided:
        print(f"    actual: {claim.status} {money(truth)}  -> {bucket(d['payout'], truth)}"
              + (f"  (diff {money(d['payout'] - truth)})" if truth is not None else ""))
    else:
        print(f"    actual: {claim.status} (not final)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Security-deposit claim payout engine")
    ap.add_argument("selection", help="tracking number, range (7-20), list (7-20,49) or 'all'")
    ap.add_argument("--detail", action="store_true", help="line-level breakdown for every claim")
    ap.add_argument("--summary", action="store_true", help="accuracy summary only")
    ap.add_argument("--json", action="store_true", help="emit JSON decisions")
    ap.add_argument("--docs-only", action="store_true", help="ignore the adjuster PM Explanation (documents + policy facts only)")
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    claims = load_claims()
    dup_of = build_duplicate_index(claims)
    ids = parse_selection(args.selection, claims)
    if not ids:
        print("no matching tracking numbers", file=sys.stderr)
        return 2
    rows, decisions = [], []
    for t in ids:
        c = claims[t]
        ext = load_extraction(t)
        d = compute(c, ext, dup_of, use_notes=not args.docs_only)
        d["has_extraction"] = ext is not None
        d["actual_status"] = c.status
        d["actual"] = c.truth
        d["verdict"] = bucket(d["payout"], c.truth) if c.is_decided else "not_final"
        decisions.append(d)
        if c.is_decided and c.status != "Test Claim" and not (d.get("decline_reason") == "test claim"):
            rows.append({"t": t, "pred": d["payout"], "truth": c.truth, "era": d["era"], "basis": d.get("basis"),
                         "ext": ext is not None, "status": c.status})
    elapsed = time.perf_counter() - t0

    if args.json:
        json.dump(decisions if len(decisions) > 1 else decisions[0], sys.stdout, indent=1, default=str)
        print()
        return 0
    if not args.summary:
        if len(ids) == 1 or args.detail:
            for t, d in zip(ids, decisions):
                detail(claims[t], d)
        else:
            print(f"{'#':>5} {'status':<12} {'actual':>11} {'computed':>11} {'diff':>10}  {'verdict':<8} basis / reason")
            for t, d in zip(ids, decisions):
                c = claims[t]
                diff = "" if c.truth is None or not c.is_decided else f"{d['payout'] - c.truth:+,.2f}"
                why = d.get("decline_reason") or d.get("basis") or ""
                print(f"{t:>5} {str(c.status)[:12]:<12} {money(c.truth) if c.is_decided else '-':>11} "
                      f"{money(d['payout']):>11} {diff:>10}  {d['verdict']:<8} {why}")
    s = summarize(rows)
    print(f"\nscored {s['n']} decided claims | exact(+/-$1) {s['exact_pct']}% | within 5%/$25 {s['within_5pct_pct']}% "
          f"| MAPE (paid) {s['mape_pct']}% | MAE {money(s['mae'])} | declines right {s['decline_accuracy_pct']}% of {s['declines']} | "
          f"$ computed {money(s['dollar_total_pred'])} vs actual {money(s['dollar_total_truth'])} | {elapsed*1000:.0f} ms")
    if args.summary:
        groups = defaultdict(list)
        for r in rows:
            groups[f"era {r['era']}"].append(r)
            groups[f"basis {r['basis']}"].append(r)
            groups["with extraction" if r["ext"] else "no extraction"].append(r)
            groups[f"status {r['status']}"].append(r)
        for k in sorted(groups):
            g = summarize(groups[k])
            print(f"  {k:<40} n={g['n']:<5} exact {g['exact_pct']:>5}%  <=5% {g['within_5pct_pct']:>5}%  MAPE {g['mape_pct']}%  MAE {money(g['mae'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
