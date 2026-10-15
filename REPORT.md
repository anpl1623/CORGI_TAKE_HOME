# Security-Deposit Claim Payout Engine — Work Trial Report

**Andrew Pleeter · Corgi work trial · 2026-10-15**

## TL;DR

I built a system that takes a tracking number (or a range) and returns a payout, a line-by-line explanation, and a comparison with the historical Approved Benefit Amount. It has three parts:

1. **Ingest.** Merges and checks the Drive dump and extracts text from every PDF, docx and xlsx (17 s for the whole book).
2. **AI extraction.** An LLM turns the messy documents into structured facts: charges by category, lease and move-out facts, credits, and decline flags. It never sees the outcome.
3. **Rules engine.** Deterministic Python holds the reverse-engineered rule book. It is auditable, every number can be tuned, and it runs in milliseconds per claim.

Metric per Corgi: **% exact match** (±$1), plus MAPE (mean absolute % error on paid claims; declines are scored right/wrong separately).

| Accuracy vs. Approved Benefit Amount | Claims | Exact (±$1) | Within 5% | MAPE | MAE |
|---|---|---|---|---|---|
| **Whole book** (every decided claim, all methods) | 1,228 | **72.8%** | 75.0% | 44.7% | $272 |
| **Held-out claims** (extracted after the rules were frozen; Gemini Flash / Haiku / Sonnet / ChatGPT) | 555 | **73.9%** | 77.5% | **10.9%** | $197 |
| Claims used to tune the rules (in-sample) | 161 | 87.0% | 89.4% | 6.8% | $68 |
| Claims with no documents (sheet + PM note + LLM comment read) | 219 | 61.6% | 62.6% | – | $363 |
| Documents with no extraction yet (pay ceiling) | ~290 | ~67% | – | ~95% | $415 |
| Sheet-only baseline (pay Max Benefit, no documents) | 1,230 | 53.3% | 53.9% | – | $679 |
| Meeting examples: #7–20 and #49 | 15 | 100% | 100% | 0% | $0 |

The honest generalization number is the **held-out 74%**. The 87% in-sample figure is optimistic. The gap comes from three things: rules fitted on those claims, a 2023-heavy held-out mix, and cheaper extraction models. The remaining ~290 documented claims weren't extracted because of a compute budget, not a design limit (extraction takes about 1 minute per claim and runs in parallel).

Total dollars computed on the extracted claims are within 1% of the actual total.

Run it:

```bash
python3 payout.py 49                 # adjuster-style breakdown
python3 payout.py 7-20               # table vs. actual
python3 payout.py all --summary      # book-wide accuracy
python3 payout.py 49 --docs-only     # ignore adjuster notes
python3 payout.py 49 --json          # machine-readable decision
```

---

## 1. Data integrity findings (found before any modeling)

| Finding | Impact | How it was handled |
|---|---|---|
| **"Amount of Claim" is corrupted.** The column is strictly ascending in tracking-number order while claim dates also ascend, so it was sorted on its own and no longer lines up with its rows. | It looks like the obvious input but is garbage. | Ignored. Claim amounts are rebuilt from the documents. |
| **The first Drive download was missing 53% of files.** Drive splits big folder zips into ~2 GB parts and spreads each claim folder's files across them. Only one part had been saved: 2,718 of 5,775 files. | Most folders were missing their key move-out statement. | Re-downloaded the full folder, merged every part (no overwrites, zip-slip guarded), and inventoried it against Drive through the Drive API. |
| **About 210 claims (#1018–1235) have no document folder on Drive at all** (verified through the Drive API). Corgi confirmed this is a known Drive issue and that having most claims is fine. | No itemization exists for them. | Sheet + PM note + LLM read of the comment thread; otherwise pay the ceiling. Reported as a separate accuracy line. |
| The Comments sheet's "Row N" refers to an older sort order of the sheet. | Naive joins put comments on the wrong claims. | Re-mapped by content (rent amounts, addresses, dates). In the end only the PM Explanation is used; comments proved noisy (below). |
| **Declined rows that hold an amount** (#440, 568, 803, 829, 1092, 1168; #673 holds note text). Every one is a claim the adjuster calculated, sometimes approved, and then killed before payment: the PM cancelled ("cheque has never gone out", #1092), the owner waived the fees, the tenant paid the PM, a prior-carrier policy, or a first-month default. | The amount looks like a payout but nothing was paid. | Truth = $0 (scored as a decline). The stored amount is kept as a secondary "calculated before cancellation" label. The engine reports `amount_if_not_declined` for every decline, so declines are auditable; it matches the adjuster's pre-cancel figure on #440 and #803. |
| Other inconsistencies: a Max Benefit below the paid amount (#540), PM notes that contradict the payout (#697, #431). | Irreducible noise. | Listed in §5. |

## 2. System design

```
Drive zips ──► ingest_zip.py ──► extract_text.py ──► digest.py ──► AI extraction ──► cache/extract/T.json
                (merge, dedupe,     (pdftotext/docx/     (per-claim text,     (facts only, blind     │
                 zip-slip guard)     xlsx; flags scans)   leases trimmed)      to the outcome)        ▼
comment thread ─► LLM comment read (no-doc claims only) ─► cache/comment_reads.json ─────────────────────────────┐
claims sheet ─► sheet.py ─────────────────────────────────────────────────────────────────► engine.py + rules.py + notes.py
                (policy facts: Max Benefit, rent, dates, PM, treaty, PM Explanation)          │
                                                                                              ▼
                                                     payout, decline reason, ceiling, per-line decisions,
                                                     credits, confidence, review flags  ──►  CLI / JSON
```

**Design choices:**

- **The AI reads; code decides.** The LLM never computes a payout. It categorizes each open charge into a 31-category taxonomy and records lease, move-out and ledger facts with evidence quotes. All coverage logic sits in `rules.py`, which is readable by an adjuster, versioned, unit-testable and cheap to change. A rule change doesn't need any document re-reading.
- **Blind extraction.** Extractors are forbidden from reading the sheet outcome, notes, or other extractions, so accuracy numbers aren't inflated by leakage.
- **Explainable output.** Every line shows covered, excluded, partial or skip, with the rule that applied. For example: `x $262.50 late fee (late fees are not covered)`.
- **Confidence and review flags.** Each claim gets a confidence score plus flags such as `flooring_without_support`, `mixed_pet_nonpet_line`, `missing_itemization` and `tenant_disputes_charges`, which route uncertain claims to a human. Claims that land on the ceiling (94.7% exact) are naturally robust.
- **Speed.** After extraction, adjudication takes about 1 ms per claim (1,244 claims in ~120 ms). Extraction is the only slow or expensive step. It is cached per claim, runs in parallel, and is model-agnostic: the same schema was produced by Claude agents and by Gemini Flash, with equal downstream accuracy.

## 3. The reverse-engineered rule book

Order of evaluation (`engine.compute`):

1. **Declines → $0.**
   - From adjuster notes: duplicate claim; not our policy / no active SD policy; prior carrier; tenant defaulted on the first full month; paid in full; payment arrangement; settled with the PM; PM cancelled or closed out; owner waived the balance; withdrawn; denied. Each phrase was checked for precision against every decided claim (47 of 48 hits are true declines).
   - From documents and the sheet: test claim (fake PM or address, rent = $1), blank Policy #, same address and move-out as an earlier claim, PM void, tenant never moved in or still in possession, tenant settled with the PM, short-term lease (≤3 months, from Sept 2024).
2. **Ceiling.**
   - Max Benefit from the sheet, but a cap the adjuster stated wins ("based on monthly rent of 1829, the benefit cannot exceed 2000", 34/39 exact).
   - Rent cap = monthly rent rounded **up** to the next $500. It applies only to Treaty T00001 claims from 2024-04-24 on leases whose current term began on or after 2023-07-01. It fits 26/33 binding cases, against 3/76 outside that window, and 134/137 adjuster cap notes use this formula.
3. **Stated amounts.** "Approved for $X" or "benefit of $X" pays X (6/7). "Paying one month rent" pays the monthly rent.
4. **Default practice: pay the PM's open balance up to the ceiling,** net of PM-applied credits (cash deposit applied, prepaid balance, rent refunds). YRIG's own later tenant settlements are never netted.
   - Exception: the flat $200 move-out coordination fee was not paid before Nov 2023.
   - This was the single biggest discovery. When there is no adjuster note, adjusters paid the PM's balance. Exclusions appear essentially only when the adjuster wrote them down: 130/161 exact with this policy, against 119/161 for applying exclusions on every claim.
5. **When the adjuster wrote a note (Nov 2023 onward), apply the exclusion rule book:**
   - **Covered:** unpaid rent while in possession and within the term; the move-out month **prorated** (rent × days ÷ days in month); cleaning, carpet cleaning, repairs, paint, flooring, trash-out, rekey, keys and remotes, appliances; infestation remediation.
   - **Lease-break bucket:** lease-break fee + reletting fee + rent after move-out within the term, **capped at one month's rent**.
   - **Sublimits:** landscaping ≤ $500. Coordination fee ≤ $200, and only for PURE (South Carolina) and New Heights. Utilities are covered in full for PMS Columbus and up to $150 for StarPointe from April 2024 (PM side agreements).
   - **Excluded:** late fees, NSF fees, admin and itemization fees, eviction, court and legal fees, SDRP premiums, RBP and renters-insurance fees, HOA charges, collection fees, misc fees (amenity, lease violation, garage, concessions), routine pest control, **pet damage and pet fees** (pet policy), **water, fire and flood damage** (renters or homeowner's policy), and **rent after lease expiration** (holdover of 3 days or less is paid).
   - If the note lists what was paid ("paying cleaning, move out repairs and make ready"), only those categories are paid.
6. **No documents.** An LLM reads the adjuster's comment thread, blind to the outcome, and returns: decline or pay, a payout amount if one is stated or can be summed (e.g. "77.50 short for April, 798 short for August, 75.00 short for Sept" sums to $950.50, exactly what was paid), any stated cap, and a confidence. Reads with confidence ≥ 0.5 are used: 85 claims, 84.7% exact. Otherwise the engine pays the ceiling.
   - Tenant settlement and collected amounts are only a lower bound (never above the payout, equal only 15% of the time), so they're not used as the payout.

The documents-only mode (`--docs-only`) runs the same rule book with era switches instead of notes: Era A/B before Nov 2023 pays the gross balance; Era C/D applies the exclusions.

## 4. Accuracy detail (documents + notes, 161 extracted claims)

| Slice | n | Exact | Within 5% | MAE |
|---|---|---|---|---|
| Era A (2022) | 23 | 100% | 100% | $0 |
| Era B (2023, until Oct) | 55 | 81.8% | 81.8% | $131 |
| Era C (Nov 2023 – Apr 2024) | 32 | 90.6% | 90.6% | $25 |
| Era D (Apr 2024 on) | 51 | 84.3% | 92.2% | $59 |
| Payout hits the ceiling | 94 | 94.7% | 94.7% | $58 |
| Itemized below the ceiling | 58 | 74.1% | 81.0% | $75 |
| Declines | 7 | 85.7% | 85.7% | – |

**Caveat on overfitting.** The rule thresholds were found on about 270 claims: 110 hand-audited in rule discovery plus the 161 extracted. The remaining ~860 claims with documents are being extracted now as a true held-out test. `python3 payout.py all --summary` reports the "with extraction" slice separately.

## 5. Where it misses (irreducible or out of scope)

- **2023 practice was inconsistent.** Some Era B claims silently excluded pet damage or fees with no note (#55, #86). Management "goodwill" payments and top-ups to Max (#454, #793, #1081) are discretionary.
- **Off-document negotiation.** "Paid as per the revised amount with tenant" (#431). Partial carpet allowances (#1164).
- **Sheet errors.** Max Benefit below the paid amount (#540). A note says "denied" but the claim was paid (#697).
- **Extraction granularity.** Payment-allocation ambiguity in ledgers (#410) and lumped balance-forward lines (#764, −$33).

## 6. Productionizing (what I'd do next)

1. **Adjuster queue.** Auto-approve high-confidence claims where the payout hits the ceiling (~95% exact). Route itemized and flagged claims to review with the line-by-line breakdown pre-filled.
2. **Make the rules explicit going forward.** The historical rules were implicit and only applied when someone wrote a note. Codify the exclusion list, rent cap and lease-break cap as written policy, so new claims are adjudicated consistently rather than replaying 2023 inconsistency.
3. **Live extraction service.** Upload documents → extract with a cheap model, falling back to vision for scans → engine → decision in seconds. Ask PMs for a structured itemization template to remove most extraction error.
4. **Regression suite.** Freeze the 1,000+ historical claims as test cases. Any rule change reports accuracy deltas by era, PM and category before it ships.
