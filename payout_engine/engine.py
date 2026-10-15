"""Payout engine: sheet policy facts + structured document extraction -> decision.

Pure, deterministic and explainable: every dollar in or out of the payout is
attached to a line-level decision and a rule from rules.py.
"""
import calendar
import json
import os
import re
from datetime import date, datetime, timedelta

from . import rules as R
from .notes import Notes
from .sheet import ROOT

EXTRACT_DIR = os.path.join(ROOT, "cache", "extract")
DOCS_DIR = os.path.join(ROOT, "Security Deposit Itemization Documents")

DAMAGE_CATEGORIES = {
    "cleaning", "carpet_cleaning", "repairs_damage", "painting", "flooring", "trash_removal",
    "rekey_locks", "keys_remotes", "appliance", "other_damage", "landscaping_lawn", "pest_remediation",
}
# Pet involvement voids interior damage/cleaning lines (637, 711, 1007) but not yard
# clean-up or trash-out that happens to include pet waste (843 landscaping paid).
PET_EXCLUDABLE = {
    "cleaning", "carpet_cleaning", "repairs_damage", "painting", "flooring", "appliance",
    "other_damage", "pest_remediation",
}


def _d(v):
    if not v:
        return None
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y-%m"):
        try:
            return datetime.strptime(s[:10] if fmt == "%Y-%m-%d" else s, fmt).date()
        except ValueError:
            continue
    return None


def _money(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return 0.0


def load_extraction(tracking):
    p = os.path.join(EXTRACT_DIR, f"{tracking}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


_COMMENT_READS = None


def load_comment_read(tracking):
    """LLM read of the comment thread for claims without documents (cache/comment_reads.json)."""
    global _COMMENT_READS
    if _COMMENT_READS is None:
        p = os.path.join(ROOT, "cache", "comment_reads.json")
        _COMMENT_READS = {}
        if os.path.exists(p):
            with open(p) as f:
                _COMMENT_READS = {int(k): v for k, v in json.load(f).items()}
    return _COMMENT_READS.get(int(tracking))


def has_documents(tracking):
    d = os.path.join(DOCS_DIR, str(tracking))
    return os.path.isdir(d) and any(not n.startswith(".") for n in os.listdir(d))


def _norm_addr(a):
    a = (a or "").lower()
    a = re.sub(r"[^a-z0-9 ]", " ", a)
    a = re.sub(r"\b(street|st|road|rd|drive|dr|lane|ln|court|ct|circle|cir|avenue|ave|trail|trl|way|unit|apt)\b", "", a)
    return re.sub(r"\s+", " ", a).strip()


def build_duplicate_index(claims):
    """Later claims for the same address + move-out (or lease start) as an
    earlier claim are duplicates (731 dup of 702; 'DUPLICATE CLAIM' notes)."""
    first = {}
    dup_of = {}
    for t in sorted(claims):
        c = claims[t]
        a = _norm_addr(c.address)
        if not a:
            continue
        key = (a, c.move_out or c.lease_start)
        if key[1] is None:
            continue
        if key in first:
            dup_of[t] = first[key]
        else:
            first[key] = t
    return dup_of


class Decision(dict):
    """dict with attribute access; serialisable as-is."""
    __getattr__ = dict.get


def _ceiling(claim, ext, rent, cd):
    """Max Benefit, tightened by the rent-based cap where it applies."""
    ceiling = claim.max_benefit
    source = "max_benefit"
    lease = (ext or {}).get("lease") or {}
    term_start = _d(lease.get("current_term_start")) or _d(lease.get("lease_start"))
    if term_start is None and claim.lease_start:
        term_start = claim.lease_start
        if claim.lease_end and (claim.lease_end - claim.lease_start).days > 400:
            term_start = claim.lease_end - timedelta(days=365)   # renewal: current term start
    treaty = claim.raw.get("Treaty #")
    cap = R.rent_cap_amount(rent)
    if cap and R.rent_cap_applies(treaty, cd, term_start):
        if ceiling is None or cap < ceiling:
            ceiling, source = cap, f"rent_cap(ceil({rent:.2f}/500)*500)"
    elif ceiling is None and cap:
        ceiling, source = cap, "rent_cap(no Max Benefit on sheet)"
    return ceiling, source


def _decline(claim, ext, cd, dup_of, first_month_rule=True):
    flags = (ext or {}).get("flags") or {}
    raw = claim.raw
    if (R.TEST_PM.search(claim.pm_company or "") or R.TEST_ADDRESS.search(claim.address or "")
            or (claim.rent is not None and claim.rent <= 1.0) or flags.get("test_claim")):
        return "test claim"
    if not raw.get("Policy"):
        return "no SD policy on file (blank Policy #)"
    if flags.get("no_policy_evidence") or flags.get("other_provider"):
        return "no active SD policy with us (cash deposit / other provider)"
    # premiums_unpaid is a review flag only: historical "premiums not paid" declines came
    # from YRIG's policy system, and unpaid SDRP lines on a PM ledger are routine (7, 18, 49).
    if claim.tracking in dup_of:
        return f"duplicate of claim {dup_of[claim.tracking]}"
    if flags.get("pm_withdrew_or_void"):
        return "PM withdrew / voided the claim"
    if flags.get("tenant_never_moved_in"):
        return "tenant never moved in"
    if flags.get("tenant_still_in_possession"):
        return "tenant still in possession"
    if flags.get("tenant_paid_or_settled_with_pm") or flags.get("payment_arrangement") or flags.get("owner_waived_balance"):
        return "tenant paid / settled / payment arrangement with PM"
    led = (ext or {}).get("ledger") or {}
    # Ledger-read first-month defaults are unreliable (4 of 5 false on the sample:
    # 387, 626, 963, 995 were paid); with notes, the adjuster's note decides instead.
    if first_month_rule and cd and cd >= R.FIRST_MONTH_DEFAULT_FROM and (
            led.get("first_full_month_paid_in_full") is False or led.get("first_payment_bounced") is True):
        return "tenant defaulted on first full month of rent"
    if cd and cd >= R.SHORT_TERM_LEASE_FROM and flags.get("short_term_lease"):
        return "short-term lease (<= 3 months) not eligible"
    return None


def _credits(ext):
    total = 0.0
    used = []
    for c in (ext or {}).get("credits") or []:
        amt = abs(_money(c.get("amount")))
        if amt and not c.get("already_netted_in_line_items") and c.get("type") in R.NETTED_CREDIT_TYPES:
            total += amt
            used.append({"description": c.get("description"), "amount": amt, "type": c.get("type")})
    return round(total, 2), used


def _prorate_move_out_month(li, amount, rent, move_out, lease_end):
    """A full month of rent billed for the move-out month is split: the
    in-possession days are rent (rent x days / days_in_month, 764: 935x4/31),
    the rest is post-move-out rent that joins the lease-break bucket.
    -> (in_possession, after_move_out) or None when no split applies."""
    start, end = _d(li.get("service_period_start")), _d(li.get("service_period_end"))
    if not (move_out and start and end and start <= move_out < end):
        return None
    if lease_end and move_out >= lease_end:
        return None
    dim = calendar.monthrange(move_out.year, move_out.month)[1]
    days = (move_out - start).days + 1
    in_poss = round(rent * days / dim, 2)
    if in_poss >= amount:
        return None
    return in_poss, round(amount - in_poss, 2)


def _line_decisions_cd(claim, ext, rent, cd, family):
    """Eras C/D: per-line coverage. Returns (lines, eligible_total)."""
    lines = []
    flags = ext.get("flags") or {}
    move = ext.get("move_out") or {}
    lease = ext.get("lease") or {}
    holdover = move.get("holdover_days_after_lease_end")
    move_out = _d(move.get("move_out_date")) or claim.move_out
    lease_end = _d(lease.get("current_term_end")) or _d(lease.get("lease_end")) or claim.lease_end
    util_ok, util_cap = R.utilities_rule(family, cd)
    buckets = {"landscaping": [], "coordination": [], "utilities": [], "lease_break": []}
    total = 0.0
    for li in ext.get("line_items") or []:
        amt = _money(li.get("amount_open"))
        cat = li.get("category") or "other_fee"
        rec = {"description": li.get("description"), "category": cat, "amount": amt, "paid": 0.0}
        lines.append(rec)
        if amt <= 0:
            rec.update(decision="skip", reason="no open amount")
            continue
        if li.get("owner_responsible") or li.get("is_estimate_only"):
            rec.update(decision="skip", reason="owner item / estimate, not billed to tenant")
            continue
        if li.get("pet_related") and cat in PET_EXCLUDABLE:
            rec.update(decision="excluded", reason=R.EXCLUDED["pet_damage_odor"])
            continue
        if cat == "rent_in_term" and rent:
            split = _prorate_move_out_month(li, amt, rent, move_out, lease_end)
            if split:
                in_poss, after = split
                rec.update(amount=in_poss, decision="covered", paid=in_poss,
                           reason=f"rent prorated to move-out {move_out} (rent x days / days in month)")
                total += in_poss
                tail = {"description": f"{li.get('description')} [after move-out portion]",
                        "category": "rent_after_move_out", "amount": after, "paid": 0.0}
                lines.append(tail)
                buckets["lease_break"].append(tail)
                continue
        if li.get("water_fire_flood") and cat in DAMAGE_CATEGORIES:
            rec.update(decision="excluded", reason="water/fire/flood damage belongs to renters/HO policy")
            continue
        if cat in R.COVERED:
            rec.update(decision="covered", reason=R.COVERED[cat], paid=amt)
            total += amt
        elif cat in R.LEASE_BREAK_BUCKET:
            if flags.get("military_scra"):
                rec.update(decision="excluded", reason="military / SCRA release: no lease-break charges")
            else:
                buckets["lease_break"].append(rec)
        elif cat == "rent_after_lease_end":
            days = li.get("days_after_lease_end")
            days = days if days is not None else holdover
            if days is not None and days <= R.HOLDOVER_GRACE_DAYS:
                rec.update(decision="covered", reason=f"holdover of {days} day(s) through move-out", paid=amt)
                total += amt
            else:
                rec.update(decision="excluded", reason="rent after lease expiration (holdover / month-to-month) is not covered")
        elif cat == "landscaping_lawn":
            buckets["landscaping"].append(rec)
        elif cat == "maintenance_coordination_fee":
            if R.coordination_fee_allowed(family):
                buckets["coordination"].append(rec)
            else:
                rec.update(decision="excluded", reason="coordination / handling fee not covered for this PM")
        elif cat == "utilities":
            if util_ok:
                buckets["utilities"].append(rec)
            else:
                rec.update(decision="excluded", reason="utilities are not covered")
        elif cat in R.EXCLUDED:
            rec.update(decision="excluded", reason=R.EXCLUDED[cat])
        else:
            rec.update(decision="excluded", reason="uncategorised charge")

    def apply_sublimit(items, limit, label):
        nonlocal total
        remaining = limit
        for rec in items:
            pay = rec["amount"] if remaining is None else min(rec["amount"], max(remaining, 0.0))
            if remaining is not None:
                remaining -= pay
            rec.update(paid=round(pay, 2), decision="covered" if pay >= rec["amount"] else "partial",
                       reason=label if pay >= rec["amount"] else f"{label} (sublimit)")
            total += pay

    apply_sublimit(buckets["landscaping"], R.LANDSCAPING_SUBLIMIT, f"landscaping, ${R.LANDSCAPING_SUBLIMIT:.0f} sublimit")
    apply_sublimit(buckets["coordination"], R.COORDINATION_FEE_SUBLIMIT, f"move-out coordination fee, ${R.COORDINATION_FEE_SUBLIMIT:.0f} sublimit")
    apply_sublimit(buckets["utilities"], util_cap, "utilities (PM agreement)" + (f", ${util_cap:.0f} sublimit" if util_cap else ""))
    lb_limit = round(rent * R.LEASE_BREAK_MONTHS, 2) if rent else None
    apply_sublimit(buckets["lease_break"], lb_limit, "lease break: fee + reletting + post-move-out rent, max one month rent")
    return lines, round(total, 2)


def _line_decisions_gross(ext, era, excluded=frozenset(), why="adjuster paid the PM's balance"):
    """Gross-balance practice: every open PM charge is paid, except categories an
    adjuster explicitly excluded (PM Explanation) and the flat coordination fee
    pre-Nov-2023 (21, 23, 40, 41, 95: always $200 short)."""
    lines, total = [], 0.0
    for li in ext.get("line_items") or []:
        amt = _money(li.get("amount_open"))
        cat = li.get("category")
        rec = {"description": li.get("description"), "category": cat, "amount": amt, "paid": 0.0}
        if amt <= 0:
            rec.update(decision="skip", reason="no open amount")
        elif li.get("owner_responsible") or li.get("is_estimate_only"):
            rec.update(decision="skip", reason="owner item / estimate, not billed to tenant")
        elif cat in excluded:
            rec.update(decision="excluded", reason="excluded per adjuster note: " + R.EXCLUDED.get(cat, cat))
        elif cat == "maintenance_coordination_fee" and era in "AB":
            rec.update(decision="excluded", reason="coordination fee not paid before Nov 2023")
        else:
            rec.update(decision="covered", reason=why, paid=amt)
            total += amt
        lines.append(rec)
    return lines, round(total, 2)


def compute(claim, ext=None, dup_of=None, use_notes=True, note_policy="full", skip_declines=False):
    """-> Decision(payout, decline_reason, era, ceiling, lines, credits, flags, confidence, explanation).

    use_notes=False is the documents-only engine (era rule book). use_notes=True
    also reads the adjuster's PM Explanation: stated declines/caps/amounts win,
    and exclusions are applied when the adjuster wrote a note (note_policy
    "full" = full exclusion rule book, "targeted" = only the named categories);
    without a note the PM's balance is paid up to the ceiling, which is how the
    historical book was actually adjudicated (130/161 vs 119/161 exact)."""
    dup_of = dup_of or {}
    cd = claim.claim_date
    e = R.era(cd)
    family = R.pm_family(claim.pm_company)
    lease = (ext or {}).get("lease") or {}
    doc_rent = _money(lease.get("base_monthly_rent")) or None
    rent = doc_rent or claim.rent
    ceiling, ceiling_source = _ceiling(claim, ext, rent, cd)
    note = Notes(claim.pm_explanation) if use_notes else Notes(None)
    if note.cap:
        ceiling, ceiling_source = note.cap, "adjuster note cap"
    out = Decision(tracking=claim.tracking, era=e, pm_family=family, rent=rent, ceiling=ceiling,
                   ceiling_source=ceiling_source, decline_reason=None, lines=[], credits=[],
                   review_flags=[], basis=None, mode="docs+notes" if use_notes else "docs-only",
                   note=note.text or None)

    def declined(reason, conf):
        # also report what the claim would have paid, so a decline is auditable
        # and declined-after-approval rows (1092, 1168...) can check the calculator
        alt = compute(claim, ext, dup_of, use_notes, note_policy, skip_declines=True)
        out.update(payout=0.0, decline_reason=reason, basis="declined", confidence=conf,
                   amount_if_not_declined=alt["payout"])
        return out

    if note.decline and not skip_declines:
        return declined("adjuster note: " + note.decline, 0.9)
    reason = None if skip_declines else _decline(claim, ext, cd, dup_of, first_month_rule=not use_notes)
    if reason:
        return declined(reason, 0.7)
    if note.stated_amount is not None:
        out.update(payout=round(note.stated_amount, 2), basis="adjuster note amount", confidence=0.9)
        return out
    if note.pay_one_month_rent and rent:
        out.update(payout=round(rent if ceiling is None else min(rent, ceiling), 2),
                   basis="adjuster note: one month rent", confidence=0.85)
        return out

    items = (ext or {}).get("line_items") or []
    flags = (ext or {}).get("flags") or {}
    if ext is None or (not items and ext.get("pm_stated_amount_due") in (None, 0)):
        read = load_comment_read(claim.tracking) if use_notes else None
        if read:
            # No documents: an LLM read of the adjuster's comment thread (blind to the outcome).
            if read.get("cap_stated") and (ceiling is None or read["cap_stated"] < ceiling):
                ceiling, out["ceiling_source"] = read["cap_stated"], "cap stated in comments"
                out["ceiling"] = ceiling
            if (read.get("decision") == "decline" and not skip_declines
                    and (read.get("confidence") or 0) >= R.COMMENT_READ_MIN_CONF):
                return declined("comments: " + (read.get("decline_reason") or "declined"), read.get("confidence"))
            est = read.get("amount_estimate")
            if est is not None and est > 0 and (read.get("confidence") or 0) >= R.COMMENT_READ_MIN_CONF:
                pay = est if ceiling is None else min(est, ceiling)
                out.update(payout=round(pay, 2), basis="amount from adjuster comments (no documents)",
                           confidence=read.get("confidence"), comment_basis=read.get("amount_basis"))
                return out
        # No usable itemization: historical outcome is the ceiling (Max) for most
        # claims (2022: 31/33; evictions 73-89%), weakest for era C/D move-outs.
        out.update(payout=ceiling if ceiling is not None else 0.0,
                   basis="no itemization -> ceiling" + ("" if has_documents(claim.tracking) else " (no documents on file)"),
                   confidence=0.6 if e in "AB" or claim.termination == "Eviction" else 0.35)
        out["review_flags"].append("missing_itemization")
        return out

    if use_notes and note and note_policy == "full" and e not in "AB":
        lines, eligible = _line_decisions_cd(claim, ext, rent, cd, family)
    elif use_notes:
        lines, eligible = _line_decisions_gross(
            ext, e, excluded=frozenset(note.excluded),
            why="no exclusion noted by adjuster: PM balance paid")
    elif e in "AB":
        lines, eligible = _line_decisions_gross(ext, e, why="pre-Nov-2023 practice: full PM balance counted")
    else:
        lines, eligible = _line_decisions_cd(claim, ext, rent, cd, family)
    if not items and ext.get("pm_stated_amount_due"):
        eligible = _money(ext["pm_stated_amount_due"])
        lines = [{"description": "PM stated balance due", "category": "balance", "amount": eligible,
                  "paid": eligible, "decision": "covered", "reason": "PM stated balance (no line detail)"}]
    if note.included:
        # adjuster listed what they paid ("paying cleaning, move out repairs and make ready"): nothing else
        for rec in lines:
            if rec.get("decision") in ("covered", "partial") and rec.get("category") not in note.included:
                eligible -= rec.get("paid") or 0.0
                rec.update(paid=0.0, decision="excluded", reason="not in the adjuster's list of paid items")
        eligible = round(eligible, 2)
    credit_total, credits = _credits(ext)
    net = round(eligible - credit_total, 2)
    out.update(lines=lines, credits=credits, eligible=eligible, credit_total=credit_total, net_eligible=net)

    if net <= 0 and e not in "AB":
        out.update(payout=0.0, decline_reason="no eligible charges after exclusions/credits", basis="declined",
                   confidence=0.6)
        return out
    payout = max(0.0, net if ceiling is None else min(net, ceiling))
    out.update(payout=round(payout, 2),
               basis="ceiling" if ceiling is not None and net >= ceiling else "itemized")

    for f in ("flooring_without_support", "mixed_pet_nonpet_line", "tenant_disputes_charges", "missing_ledger"):
        if flags.get(f):
            out["review_flags"].append(f)
    conf = float(ext.get("extraction_confidence") or 0.7)
    if out["basis"] == "ceiling":
        conf = max(conf, 0.85)          # far above the ceiling: robust to extraction noise
    out["confidence"] = round(conf - 0.1 * len(out["review_flags"]), 2)
    return out
