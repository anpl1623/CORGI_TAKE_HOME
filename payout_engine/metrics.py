"""Accuracy metrics: computed payout vs the sheet's Approved Benefit Amount."""


def bucket(pred, truth):
    if pred is None or truth is None:
        return "no_prediction" if truth is not None else "no_truth"
    err = abs(pred - truth)
    if err <= 1.0:
        return "exact"          # within $1 (cents / rounding)
    if err <= max(25.0, 0.05 * truth):
        return "close"          # within $25 or 5%
    if err <= max(100.0, 0.15 * truth):
        return "near"           # within $100 or 15%
    return "miss"


def summarize(rows):
    """rows: iterable of dicts with keys pred, truth (floats or None)."""
    rows = [r for r in rows if r.get("truth") is not None]
    n = len(rows)
    counts = {"exact": 0, "close": 0, "near": 0, "miss": 0, "no_prediction": 0}
    abs_err = 0.0
    pred_total = truth_total = 0.0
    scored = 0
    ape = []                 # absolute percent errors, paid claims only (truth > 0)
    cent = 0                 # exact to the cent
    dec_n = dec_ok = 0       # declines (truth == 0): scored as right/wrong, not in MAPE
    for r in rows:
        b = bucket(r.get("pred"), r["truth"])
        counts[b] = counts.get(b, 0) + 1
        if r.get("pred") is not None:
            abs_err += abs(r["pred"] - r["truth"])
            pred_total += r["pred"]
            truth_total += r["truth"]
            scored += 1
            cent += abs(r["pred"] - r["truth"]) < 0.005
            if r["truth"] > 0:
                ape.append(abs(r["pred"] - r["truth"]) / r["truth"])
            else:
                dec_n += 1
                dec_ok += r["pred"] == 0
    pct = lambda k: round(100.0 * counts[k] / n, 1) if n else 0.0
    return {
        "n": n,
        **counts,
        "exact_pct": pct("exact"),
        "within_5pct_pct": round(100.0 * (counts["exact"] + counts["close"]) / n, 1) if n else 0.0,
        "within_15pct_pct": round(100.0 * (counts["exact"] + counts["close"] + counts["near"]) / n, 1) if n else 0.0,
        "mae": round(abs_err / scored, 2) if scored else None,
        "mape_pct": round(100.0 * sum(ape) / len(ape), 1) if ape else None,
        "median_ape_pct": round(100.0 * sorted(ape)[len(ape) // 2], 1) if ape else None,
        "exact_cent_pct": round(100.0 * cent / n, 1) if n else 0.0,
        "declines": dec_n,
        "decline_accuracy_pct": round(100.0 * dec_ok / dec_n, 1) if dec_n else None,
        "dollar_total_pred": round(pred_total, 2),
        "dollar_total_truth": round(truth_total, 2),
    }
