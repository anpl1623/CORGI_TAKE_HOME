"""Rebuild cache/sheet.json from the claims workbook (all columns, JSON-safe).

usage: python payout_engine/build_sheet.py CORGi_Security_Deposit_Claims.xlsx
"""
import json
import math
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _clean(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()[:10]
    if isinstance(v, float) and math.isnan(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "CORGi_Security_Deposit_Claims.xlsx")
    df = pd.read_excel(src, sheet_name="Security Deposit Claims")
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")])
    rows = {}
    for _, r in df.iterrows():
        rec = {k: _clean(v) for k, v in r.items()}
        rows[int(r["Tracking Number"])] = {k: v for k, v in rec.items() if v is not None}
    out = os.path.join(ROOT, "cache", "sheet.json")
    with open(out, "w") as f:
        json.dump(rows, f, indent=0, default=str)
    print(f"wrote {len(rows)} claims to {out}")
