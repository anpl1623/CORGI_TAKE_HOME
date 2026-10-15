"""Reverse-engineered adjudication rules (the "rule book").

Everything an adjuster would want to tune lives here, separate from the
engine mechanics in engine.py. Each rule cites the evidence that produced it
(tracking numbers from the historical book, adjuster notes, Comments sheet).
"""
import math
import re
from datetime import date

# ---------------------------------------------------------------------------
# Eras. Adjudication practice changed over time (new adjuster + "our program
# started 12/1/23" + July-2023 rate-table guidelines). Keyed on Claim Date.
# ---------------------------------------------------------------------------
ERA_B_START = date(2023, 1, 1)     # 2022 claims: almost always paid Max (31/33)
ERA_C_START = date(2023, 11, 1)    # itemized exclusions start (late fees, premiums, pet, holdover...)
ERA_D_START = date(2024, 4, 24)    # T00001 rent cap consistently enforced, sublimits appear

FIRST_MONTH_DEFAULT_FROM = date(2023, 11, 27)   # "tenant defaulted on first full month" declines
SHORT_TERM_LEASE_FROM = date(2024, 9, 1)        # short-term (<=3 mo) lease declines (818, 956)
RENT_CAP_TERM_START_FROM = date(2023, 7, 1)     # July 2023 rate-table guidelines


def era(claim_date):
    if claim_date is None:
        return "D"
    if claim_date < ERA_B_START:
        return "A"
    if claim_date < ERA_C_START:
        return "B"
    if claim_date < ERA_D_START:
        return "C"
    return "D"


# ---------------------------------------------------------------------------
# Line-item coverage for eras C/D. Eras A/B pay min(gross PM balance, Max).
# ---------------------------------------------------------------------------
COVERED = {
    "rent_in_term": "unpaid rent while in possession within the lease term",
    "cleaning": "move-out cleaning",
    "carpet_cleaning": "carpet cleaning (non-pet)",
    "repairs_damage": "damage beyond normal wear and tear",
    "painting": "painting / touch-up for tenant damage",
    "flooring": "flooring repair/replacement (non-pet, non-water)",
    "trash_removal": "trash-out / item removal",
    "rekey_locks": "rekey / lock change",
    "keys_remotes": "missing keys / remotes",
    "appliance": "appliance damage",
    "other_damage": "other physical damage",
    "pest_remediation": "infestation remediation found at move-out (783, 843)",
}

EXCLUDED = {
    "late_fee": "late fees are not covered",
    "nsf_fee": "NSF / returned-payment fees are not covered",
    "admin_itemization_fee": "admin / itemization / processing fees are not covered",
    "eviction_legal_court": "eviction, court and legal fees are not covered",
    "sdrp_premium": "unpaid SDRP / fee-in-lieu premiums are not covered",
    "rbp_insurance_liability_fee": "RBP / renters-insurance / liability fees are not covered",
    "pet_damage_odor": "pet damage belongs to the pet policy / pet deposit",
    "pet_fee_rent": "pet rent and pet fees are not covered",
    "hoa_violation": "HOA violations are not covered",
    "collections_fee": "collection fees are not covered",
    "other_fee": "miscellaneous fees (amenity, lease violation, garage, concessions...) are not covered",
    "pest_routine": "routine / preventive pest control and gutter cleaning are not covered",
}

LEASE_BREAK_BUCKET = {"rent_after_move_out", "lease_break_fee", "reletting_fee"}
LEASE_BREAK_MONTHS = 1.0           # bucket paid up to one month of base rent (752, 1000, 1213, 1162)

HOLDOVER_GRACE_DAYS = 3            # holdover <= 3 days through move-out is paid (393, 952, 935)

LANDSCAPING_SUBLIMIT = 500.0       # 730, 858, 1102
COORDINATION_FEE_SUBLIMIT = 200.0  # PURE SC / New Heights flat fee (311, 468, 661, 830)
STARPOINTE_UTILITIES_SUBLIMIT = 150.0
STARPOINTE_UTILITIES_FROM = date(2024, 4, 1)

# Credits the PM applied that reduce what the tenant owes. YRIG's own later
# tenant settlements/collections are never netted (300, 488, 627, 952, 1013).
NETTED_CREDIT_TYPES = {
    "security_deposit_applied", "pet_deposit_applied", "prepaid_credit_balance",
    "receipt_credit", "rent_refund_relet", "concession_or_reversal", "tenant_payment",
}


# ---------------------------------------------------------------------------
# Property-manager families and side agreements.
# ---------------------------------------------------------------------------
def pm_family(name):
    n = (name or "").lower()
    if "pure" in n:
        return "pure_alabama" if "alabama" in n or "huntsville" in n else "pure"
    if "new heights" in n:
        return "new_heights"
    if "columbus" in n:
        return "pms_columbus"
    if "starpointe" in n or "star pointe" in n:
        return "starpointe"
    for key in ("perry reid", "excalibur", "rentwerx", "blue fox", "johnson", "gdaa", "reliant", "1st choice", "first choice"):
        if key in n:
            return key.replace(" ", "_")
    return "other"


def coordination_fee_allowed(family):
    return family in ("pure", "new_heights")


def utilities_rule(family, claim_date):
    """-> (covered: bool, sublimit or None)."""
    if family == "pms_columbus":
        return True, None
    if family == "starpointe" and claim_date and claim_date >= STARPOINTE_UTILITIES_FROM:
        return True, STARPOINTE_UTILITIES_SUBLIMIT
    return False, None


# ---------------------------------------------------------------------------
# Rent-based benefit cap: ceil(rent / 500) * 500 ("Based on monthly rent of
# 1829.00, the maximum benefit cannot exceed 2000"; 134/137 notes match).
# Enforced for Treaty T00001 claims from 2024-04-24 on policies whose current
# term started on/after 2023-07-01 (26/33 binding cases vs 3/76 otherwise).
# ---------------------------------------------------------------------------
def rent_cap_amount(rent):
    if not rent or rent <= 0:
        return None
    return math.ceil(round(rent, 2) / 500.0) * 500.0


def rent_cap_applies(treaty, claim_date, term_start):
    if treaty != "T00001" or claim_date is None or claim_date < ERA_D_START:
        return False
    if term_start is None:
        return True
    return term_start >= RENT_CAP_TERM_START_FROM


# ---------------------------------------------------------------------------
# Test-claim fingerprints (246, 247, 591, 861, 862).
# ---------------------------------------------------------------------------
TEST_PM = re.compile(r"\b(best pm|test pm|yrig inc)\b", re.I)
TEST_ADDRESS = re.compile(r"^\s*123 main", re.I)

# Minimum confidence for using an LLM read of the adjuster comments on claims
# that have no documents (decline or payout amount).
COMMENT_READ_MIN_CONF = 0.5
