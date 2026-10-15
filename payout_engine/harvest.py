"""Copy structured extractions out of extraction-workflow journals into
cache/extract/<tracking>.json (one file per claim, newest run wins).

usage: python -I payout_engine/harvest.py <journal.jsonl> [...]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "cache", "extract")


def harvest(journal, overwrite=True):
    run = os.path.basename(os.path.dirname(journal))
    n = 0
    with open(journal) as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("type") != "result" or not isinstance(rec.get("result"), dict):
                continue
            for claim in rec["result"].get("claims") or []:
                t = claim.get("tracking")
                if not isinstance(t, int):
                    continue
                claim["_meta"] = {"run": run, "agent": rec.get("agentId")}
                path = os.path.join(OUT, f"{t}.json")
                if not overwrite and os.path.exists(path):
                    continue
                with open(path, "w") as out:
                    json.dump(claim, out, indent=1)
                n += 1
    return n


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = [a for a in sys.argv[1:] if a != "--no-overwrite"]
    for j in args:
        print(j, harvest(j, overwrite="--no-overwrite" not in sys.argv))
