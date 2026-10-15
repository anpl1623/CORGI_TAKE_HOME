"""Export engine decisions + evaluation metrics as static JSON for the Next.js UI.

usage: python3 payout_engine/export_ui.py   ->  ui/data/{summary,metrics}.json, ui/data/claims/T.json
"""
import json
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from payout_engine import engine as E  # noqa: E402
from payout_engine.metrics import bucket, summarize  # noqa: E402
from payout_engine.sheet import ROOT, load_claims  # noqa: E402

OUT = os.path.join(ROOT, "ui", "data")
SOURCES = {
    "wf_28e9d766-73c": "opus", "wf_ba0a8fba-7d1": "opus", "wf_3643befa-057": "opus", "wf_f7f175fa-0bc": "opus",
    "wf_9f183f6d-842": "sonnet", "wf_c00934e2-f06": "sonnet",
    "wf_687d7294-ad1": "haiku", "wf_72f263a2-488": "haiku", "wf_8cb38453-46f": "haiku-mini",
}


def source_of(ext):
    if ext is None:
        return None
    run = (ext.get("_meta") or {}).get("run")
    return SOURCES.get(run, "gemini/chatgpt" if run is None else "claude")


def main():
    os.makedirs(os.path.join(OUT, "claims"), exist_ok=True)
    claims = load_claims()
    dup = E.build_duplicate_index(claims)
    heldout = {int(x) for x in open(os.path.join(ROOT, "cache", "gemini_batch2.txt")).read().split()}

    summary, groups = [], defaultdict(list)
    ablation = {"docs-only": [], "docs + notes": []}
    t0 = time.perf_counter()
    for t in sorted(claims):
        c = claims[t]
        ext = E.load_extraction(t)
        d = E.compute(c, ext, dup)
        decided = c.is_decided and c.status != "Test Claim" and d.get("decline_reason") != "test claim"
        src = source_of(ext)
        row = {
            "t": t, "status": c.status, "actual": c.truth if c.is_decided else None, "payout": d["payout"],
            "verdict": bucket(d["payout"], c.truth) if c.is_decided else "open",
            "basis": d.get("basis"), "decline": d.get("decline_reason"), "era": d["era"], "pm": c.pm_company,
            "family": d["pm_family"], "treaty": c.raw.get("Treaty #"), "date": str(c.claim_date or ""),
            "max": c.max_benefit, "ceiling": d.get("ceiling"), "conf": d.get("confidence"),
            "flags": d.get("review_flags") or [], "termination": c.termination, "source": src,
            "docs": E.has_documents(t), "heldout": bool(ext is not None and t in heldout),
        }
        summary.append(row)
        detail = dict(d)
        detail.update(address=c.address, city=c.raw.get("Lease City"), state=c.raw.get("Lease State"),
                      pm=c.pm_company, status=c.status, actual=row["actual"], verdict=row["verdict"],
                      max_benefit=c.max_benefit, claim_date=row["date"], lease_start=str(c.lease_start or ""),
                      lease_end=str(c.lease_end or ""), move_out=str(c.move_out or ""), termination=c.termination,
                      source=src, pre_decline_amount=c.pre_decline_amount,
                      docs_only_payout=E.compute(c, ext, dup, use_notes=False)["payout"])
        with open(os.path.join(OUT, "claims", f"{t}.json"), "w") as f:
            json.dump(detail, f, default=str)
        if not decided:
            continue
        r = {"pred": d["payout"], "truth": c.truth}
        groups["all"].append(r)
        groups["era:" + d["era"]].append(r)
        groups["basis:" + (d.get("basis") or "").split(" (")[0]].append(r)
        groups["source:" + (src or "none")].append(r)
        groups["set:" + ("held-out" if row["heldout"] else "in-sample" if ext is not None else
                         "no documents" if not row["docs"] else "documents, not extracted")].append(r)
        groups["termination:" + (c.termination or "n/a")].append(r)
        groups["family:" + row["family"]].append(r)
        if ext is not None:
            ablation["docs + notes"].append(r)
            ablation["docs-only"].append({"pred": E.compute(c, ext, dup, use_notes=False)["payout"], "truth": c.truth})
    elapsed_ms = (time.perf_counter() - t0) * 1000

    def pack(rows):
        s = summarize(rows)
        return {k: s[k] for k in ("n", "exact_pct", "within_5pct_pct", "within_15pct_pct", "mape_pct",
                                  "median_ape_pct", "mae", "decline_accuracy_pct", "declines",
                                  "dollar_total_pred", "dollar_total_truth")}

    # decline confusion (decided claims): predicted $0 vs actually declined
    tp = fp = fn = tn = 0
    for row in summary:
        if row["verdict"] == "open" or row["status"] == "Test Claim" or row["decline"] == "test claim":
            continue
        pred0, act0 = row["payout"] == 0, row["actual"] == 0
        tp += pred0 and act0; fp += pred0 and not act0; fn += (not pred0) and act0; tn += (not pred0) and not act0
    # error histogram on paid claims
    bins = [("exact (<= $1)", 0, 1), ("$1-25", 1, 25), ("$25-100", 25, 100), ("$100-500", 100, 500),
            ("$500-1k", 500, 1000), ("> $1k", 1000, 1e12)]
    errs = [abs(r["pred"] - r["truth"]) for r in groups["all"] if r["truth"] is not None]
    hist = [{"bin": name, "n": sum(1 for e in errs if (e <= hi if lo == 0 else lo < e <= hi))} for name, lo, hi in bins]
    metrics = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "engine_ms_all_claims": round(elapsed_ms, 1),
        "claims_total": len(summary),
        "extracted": sum(1 for r in summary if r["source"]),
        "groups": {k: pack(v) for k, v in sorted(groups.items())},
        "ablation": {k: pack(v) for k, v in ablation.items()},
        "declines": {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                     "precision": round(100 * tp / (tp + fp), 1) if tp + fp else None,
                     "recall": round(100 * tp / (tp + fn), 1) if tp + fn else None},
        "error_hist": hist,
        "scatter": [{"t": r["t"], "actual": r["actual"], "payout": r["payout"], "verdict": r["verdict"]}
                    for r in summary if r["verdict"] not in ("open",) and r["actual"] is not None],
    }
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, default=str)
    with open(os.path.join(OUT, "metrics.json"), "w") as f:
        json.dump(metrics, f, default=str)
    print(f"exported {len(summary)} claims, {len(groups)} groups, engine {elapsed_ms:.0f} ms")


if __name__ == "__main__":
    main()
