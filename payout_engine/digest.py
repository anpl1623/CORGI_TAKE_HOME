"""Stage 2 input: compact per-claim digest for the AI structuring stage.

Leases are 20-60 pages of boilerplate; we keep only lines that mention rent,
deposits, term dates, fees or early termination (with a little context).
Everything else (ledgers, move-out statements, invoices) is kept in full up
to a per-file limit. Files with no extractable text are listed so the
structuring agent can open them visually.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, "cache", "text")
OUT = os.path.join(ROOT, "cache", "digest")
DOCS = os.path.join(ROOT, "Security Deposit Itemization Documents")
SHEET = os.path.join(ROOT, "cache", "sheet.json")

FILE_LIMIT = 40000
LEASE_KEYS = re.compile(
    r"(monthly rent|rent (of|is|shall|amount)|base rent|security deposit|deposit replacement|sdrp|"
    r"commenc|terminat|expir|lease term|beginning on|ending on|early termination|lease break|"
    r"reletting|re-letting|month[- ]to[- ]month|holdover|late (fee|charge)|pet (fee|rent|deposit)|"
    r"\$\s?\d)",
    re.I,
)
SHEET_FIELDS = [
    "Tracking Number", "Claim Date", "Lease Street Address", "Lease City", "Lease State",
    "Lease Start Date", "Lease End Date", "Move-Out Date", "Monthly Rent", "Termination Type",
    "Property Management Company", "Group #", "Treaty #", "Policy", "Max Benefit",
]


def is_lease(f):
    n = f["file"].lower()
    t = f.get("text", "")[:6000].lower()
    if "lease" in n and not any(k in n for k in ("addendum", "break", "ledger", "violation")):
        return True
    if (f.get("pages") or 0) >= 6 and any(k in t for k in ("lease agreement", "residential lease", "rental agreement")):
        return True
    return False


def squeeze(text):
    text = re.sub(r"[ \t]{3,}", "  ", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def lease_excerpt(text):
    lines = text.splitlines()
    keep = set()
    for i, ln in enumerate(lines):
        if LEASE_KEYS.search(ln):
            keep.update(range(max(0, i - 1), min(len(lines), i + 2)))
    out = "\n".join(lines[i] for i in sorted(keep))
    return squeeze(out)[:12000]


def build(tracking, sheet):
    with open(os.path.join(TEXT, f"{tracking}.json")) as f:
        d = json.load(f)
    row = sheet.get(str(tracking), {})
    parts = [f"# CLAIM {tracking}", "## Sheet facts (Amount of Claim column intentionally omitted: corrupted)"]
    for k in SHEET_FIELDS:
        if k in row:
            parts.append(f"- {k}: {row[k]}")
    vision = []
    for f in d["files"]:
        path = os.path.join(DOCS, str(tracking), f["file"])
        header = f"\n## FILE: {f['file']} ({f['ext']}, {f.get('pages') or '?'} pages, {f['bytes']} bytes)"
        if f.get("needs_vision"):
            vision.append(path)
            parts.append(header + "\n[NO TEXT LAYER - open visually: " + path + "]")
            continue
        text = f.get("text", "")
        if is_lease(f):
            parts.append(header + " [LEASE - keyword excerpt only; open original if a fact is missing]\n" + lease_excerpt(text))
        else:
            t = squeeze(text)
            if len(t) > FILE_LIMIT:
                t = t[:FILE_LIMIT] + f"\n[TRUNCATED at {FILE_LIMIT} chars - open original for the rest: {path}]"
            parts.append(header + "\n" + t)
    return "\n".join(parts), vision


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    with open(SHEET) as f:
        sheet = json.load(f)
    ids = sorted((int(p[:-5]) for p in os.listdir(TEXT) if p.endswith(".json")))
    if len(sys.argv) > 1:
        ids = [int(a) for a in sys.argv[1:]]
    index = {}
    for t in ids:
        text, vision = build(t, sheet)
        with open(os.path.join(OUT, f"{t}.md"), "w") as f:
            f.write(text)
        index[t] = {"chars": len(text), "vision_files": vision}
    with open(os.path.join(OUT, "_index.json"), "w") as f:
        json.dump(index, f, indent=0)
    sizes = sorted(v["chars"] for v in index.values())
    print(len(index), "median", sizes[len(sizes) // 2], "p90", sizes[int(len(sizes) * 0.9)], "max", sizes[-1],
          "vision files", sum(len(v["vision_files"]) for v in index.values()))
