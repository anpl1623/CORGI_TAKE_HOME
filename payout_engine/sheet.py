"""Claims-sheet access. The sheet is the only source of ground truth
(Approved Benefit Amount) and of policy facts (Max Benefit, rent, dates)."""
import json
import math
import os
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET_JSON = os.path.join(ROOT, "cache", "sheet.json")
PAID_STATUSES = {"Posted", "Approved", "Approved Revised"}
OPEN_STATUSES = {"In Process", "New", "Pending Docs from PM", "HOLD"}


def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return None if (isinstance(v, float) and math.isnan(v)) else float(v)
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _date(v):
    if not v or v == "NaT":
        return None
    if isinstance(v, (date, datetime)):
        return v if isinstance(v, date) else v.date()
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


class Claim:
    """One row of the claims sheet, normalised."""

    def __init__(self, row):
        self.raw = row
        self.tracking = int(row["Tracking Number"])
        self.status = row.get("Status")
        self.approved = _num(row.get("Approved Benefit Amount"))
        self.max_benefit = _num(row.get("Max Benefit"))
        self.rent = _num(row.get("Monthly Rent"))
        self.claim_date = _date(row.get("Claim Date"))
        self.lease_start = _date(row.get("Lease Start Date"))
        self.lease_end = _date(row.get("Lease End Date"))
        self.move_out = _date(row.get("Move-Out Date"))
        self.termination = row.get("Termination Type")
        self.pm_company = row.get("Property Management Company")
        self.pm_explanation = row.get("PM Explanation")
        self.address = row.get("Lease Street Address")
        # Declined rows sometimes keep the amount the adjuster had calculated/approved
        # before the claim was cancelled (1092: approved, "cheque has never gone out").
        # Nothing was paid, so truth stays $0; this is kept as a secondary label.
        self.pre_decline_amount = self.approved if self.status == "Declined" and self.approved else None

    @property
    def is_paid(self):
        return self.status in PAID_STATUSES

    @property
    def is_decided(self):
        """Has a final adjuster decision we can score against."""
        return self.status in PAID_STATUSES or self.status == "Declined"

    @property
    def truth(self):
        """Ground-truth payout: Declined -> 0 regardless of stray values."""
        if self.status == "Declined":
            return 0.0
        return self.approved


def load_claims():
    with open(SHEET_JSON) as f:
        rows = json.load(f)
    return {int(k): Claim(v) for k, v in rows.items()}


def parse_selection(spec, claims):
    """'49' | '7-20' | '7-20,49,100' | 'all' | 'open' -> sorted tracking numbers present in the sheet."""
    if spec in ("all", "*"):
        return sorted(claims)
    if spec == "open":      # live queue: no final decision yet (HOLD, Pending Docs, In Process, New)
        return sorted(t for t, c in claims.items() if c.status in OPEN_STATUSES)
    out = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return sorted(t for t in out if t in claims)
