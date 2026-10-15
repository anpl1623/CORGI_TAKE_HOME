"""Ingest a Google Drive zip (full-folder part or a folder selection) into the
master docs tree without overwriting, then refresh text + digest caches for
every claim folder that gained files.

Drive splits big folder downloads into ~2 GB parts and spreads each claim
folder's files across parts, so every part must be ingested; a claim folder
is only complete once all parts are in.

usage: python -I payout_engine/ingest_zip.py <zip> [<zip> ...]
"""
import filecmp
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "Security Deposit Itemization Documents")
STAGING = os.path.join(ROOT, "_staging")
CACHE_TEXT = os.path.join(ROOT, "cache", "text")


def claim_relpath(name):
    """Map a zip member to '<tracking>/<file...>' or None (strips a top folder)."""
    parts = [p for p in name.replace("\\", "/").split("/") if p not in ("", ".")]
    while parts and not parts[0].isdigit():
        parts = parts[1:]
    if len(parts) < 2:
        return None
    return "/".join(parts)


def ingest(zip_path):
    stage = os.path.join(STAGING, os.path.splitext(os.path.basename(zip_path))[0])
    os.makedirs(stage, exist_ok=True)
    added = same = differ = 0
    touched = set()
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = claim_relpath(info.filename)
            if rel is None or os.path.basename(rel) == ".DS_Store":
                continue
            # zip-slip guard: resolved destination must stay inside DOCS
            dest = os.path.realpath(os.path.join(DOCS, rel))
            if not dest.startswith(os.path.realpath(DOCS) + os.sep):
                print("SKIP unsafe path", info.filename)
                continue
            staged = os.path.join(stage, rel)
            os.makedirs(os.path.dirname(staged), exist_ok=True)
            with z.open(info) as src, open(staged, "wb") as out:
                shutil.copyfileobj(src, out)
            if os.path.exists(dest):
                if filecmp.cmp(staged, dest, shallow=False):
                    same += 1
                else:
                    differ += 1
                    print("CONFLICT kept existing:", rel)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(staged, dest)
            added += 1
            touched.add(rel.split("/")[0])
    shutil.rmtree(stage, ignore_errors=True)
    print(f"{os.path.basename(zip_path)}: added {added}, identical {same}, conflicts {differ}, folders touched {len(touched)}")
    return touched


if __name__ == "__main__":
    all_touched = set()
    for zp in sys.argv[1:]:
        all_touched |= ingest(zp)
    if all_touched:
        ids = sorted(all_touched, key=int)
        for t in ids:
            p = os.path.join(CACHE_TEXT, f"{t}.json")
            if os.path.exists(p):
                os.remove(p)
        with open(os.path.join(ROOT, "cache", "touched.txt"), "a") as f:
            f.write("\n".join(ids) + "\n")
        here = os.path.dirname(os.path.abspath(__file__))
        subprocess.run([sys.executable, "-I", os.path.join(here, "extract_text.py"), *ids], check=True)
        subprocess.run([sys.executable, "-I", os.path.join(here, "digest.py")], check=True)
