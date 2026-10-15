# Security-Deposit Claim Payout Engine

Corgi work trial. Given a tracking number (or a range), the engine computes the claim payout, explains each line,
and compares the result to the historical **Approved Benefit Amount**.

**Results:** 71.7% exact over the whole book. On 508 held-out claims it is 72.4% exact with MAPE 11.5%. The meeting
examples (#7–20 and #49) are 100% exact. See [REPORT.md](REPORT.md) for the findings, rule book, accuracy and design.

## Run it (Python 3.10+, standard library only)

```bash
python3 payout.py 49                 # adjuster-style breakdown for one claim
python3 payout.py 7-20               # table vs. actual approved amount
python3 payout.py 7-20,49 --detail   # breakdown for each claim
python3 payout.py open               # recommendations for open claims (HOLD / Pending / In Process / New)
python3 payout.py all --summary      # accuracy: exact %, within 5%, MAPE, MAE, declines; by era / basis
python3 payout.py 49 --docs-only     # ignore the adjuster's PM Explanation
python3 payout.py 49 --json          # machine-readable decision
```

## How it works

```
Drive zips → ingest_zip.py → extract_text.py → digest.py → AI extraction (facts only, blind to the outcome) → cache/extract/T.json
claims xlsx → build_sheet.py → cache/sheet.json ──────────────────────────────────────────────────────────┐
comment threads (no-doc claims) → LLM read → cache/comment_reads.json ──────────────────────────────────┤
                                                              engine.py + rules.py + notes.py ◄──────────┘
                                                              → payout, decline reason, ceiling, per-line decisions,
                                                                credits, confidence, review flags
```

| File | Role |
|---|---|
| `payout_engine/rules.py` | The rule book: eras, covered and excluded categories, lease-break cap, sublimits, rent cap, PM agreements |
| `payout_engine/engine.py` | Deterministic adjudication. Every dollar is tied to a rule. |
| `payout_engine/notes.py` | Parses the PM Explanation: declines, stated caps and amounts, named exclusions |
| `payout_engine/metrics.py` | Exact %, within 5%, MAPE, MAE, decline accuracy |
| `payout_engine/ingest_zip.py`, `extract_text.py`, `digest.py` | Data ingestion: safe zip merge, text extraction, per-claim digests |
| `payout_engine/harvest.py` | Collects AI extractions into `cache/extract/` |
| `GEMINI_EXTRACTION_PROMPT.md` | The extraction spec (schema + document-handling rules). It works with any LLM. |
| `cache/extract/` | Structured facts for 675 claims (the AI extraction output) |
| `cache/understand/` | Rule-discovery evidence: 110 hand-audited claims, mined adjuster notes, quantitative analysis |

## Rebuild from raw data

```bash
python3 payout_engine/build_sheet.py CORGi_Security_Deposit_Claims.xlsx
python3 payout_engine/ingest_zip.py "<drive zip part>.zip" ...
```

`build_sheet.py` needs pandas and openpyxl. `ingest_zip.py` merges every part and then runs `extract_text.py` and `digest.py`, which need `pdftotext` and python-docx. Raw documents and caches are excluded by `.gitignore`. They contain tenant PII and total 4.6 GB.
