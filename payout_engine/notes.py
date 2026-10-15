"""Adjuster-note parser (PM Explanation column).

Corgi confirmed the PM Explanation and Comments may be used as inputs. Measured
on every decided claim, the PM Explanation is high-precision (stated caps match
the payout 34/39, decline phrases 39/40, "approved for X" 6/7) while the
Comments sheet is noisy (2023 cap remarks were flagged but not applied: 4/76),
so only the PM Explanation drives decisions.
"""
import re

_NUM = r"\$?\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?\s?(k\b)?"

CAP = re.compile(
    r"(?:cannot|can not|can't|should not have|should not|not to|could not|shall not)\s+(?:have\s+)?"
    r"exceed(?:ed)?\s+(?:the\s+)?(?:amount of\s+)?" + _NUM, re.I)
APPROVED = re.compile(r"approved\s+(?:for|amount(?: is)?(?: for)?|total of|the)?\s*" + _NUM, re.I)
BENEFIT_OF = re.compile(r"benefit of\s+" + _NUM, re.I)

DECLINES = [
    ("duplicate claim", re.compile(r"duplicate claim", re.I)),
    ("not our policy / no active SD policy", re.compile(
        r"not our policy|not in our system|no (?:current |active )?sd policy|does not (?:have )?(?:an? )?sd policy", re.I)),
    ("policy with prior carrier", re.compile(r"prior carrier", re.I)),
    ("tenant defaulted on first full month of rent", re.compile(r"defaulted on (?:the )?(?:full )?(?:1st|first)|(?:1st|first) full month", re.I)),
    ("PM cancelled / closed out the claim", re.compile(r"\bcancel+ed\b|\bcancel the claim|rescind|close(?:d)? ?out per pm|closing (?:the )?claim", re.I)),
    ("owner waived the balance", re.compile(r"(?:fees|balance|charges) (?:are|were|is|was) (?:being )?waived|owner waived|waived (?:all|the) (?:fees|balance|charges)", re.I)),
    ("tenant paid in full / no balance", re.compile(r"paid in full|no balance|zero balance", re.I)),
    ("payment arrangement with PM", re.compile(r"payment arrangement", re.I)),
    ("tenant settled with PM", re.compile(r"tenant (?:has )?settled|settled with (?:the )?pm|settled directly|pay the negotiated amount directly", re.I)),
    ("claim withdrawn / closed", re.compile(r"withdr[ae]w|\bvoid\b|claim closed|close the claim", re.I)),
    ("claim denied", re.compile(r"\bdenied\b|claim (?:is |has been |was )?declined", re.I)),
]

# "No coverage for X" -> taxonomy categories to exclude.
EXCLUSION_KEYWORDS = [
    (r"late (?:fee|charge)", {"late_fee"}),
    (r"nsf|returned (?:payment|check|cheque)|stop pay", {"nsf_fee"}),
    (r"itemization|admin|paper payment|in[- ]office|convenience|mark ?up|processing", {"admin_itemization_fee"}),
    (r"sdrp|sd (?:premium|fee|charge|policy|deposit)|security deposit (?:fee|charge|premium)|fee in lieu|sdro", {"sdrp_premium"}),
    (r"\brbp\b|\btbp\b|renter'?s? (?:insurance|liability)|liability|insurance fee|ris plan", {"rbp_insurance_liability_fee"}),
    (r"utilit|water|sewer|electric|\bgas\b|trash service", {"utilities"}),
    (r"\bpet|ozone|deodoriz|flea", {"pet_damage_odor", "pet_fee_rent"}),
    (r"pest|gutter", {"pest_routine", "pest_remediation"}),
    (r"evict|court|legal|attorney|filing|posting|notice|writ", {"eviction_legal_court"}),
    (r"\bhoa\b|misc\.? income", {"hoa_violation"}),
    (r"amenit|lease violation|asset protection|garage|concession|re-?inspection|risk mitigation", {"other_fee"}),
    (r"landscap|lawn", {"landscaping_lawn"}),
    (r"holdover|month to month|month-to-month|after the lease (?:expir|end)|beyond the lease end|post the (?:original )?lease|lease (?:has )?(?:ended|expired)", {"rent_after_lease_end"}),
    (r"relet|re-let|leasing (?:fee|commission)", {"reletting_fee"}),
    (r"coordination", {"maintenance_coordination_fee"}),
    (r"collection", {"collections_fee"}),
]
_DAMAGE = {"cleaning", "carpet_cleaning", "repairs_damage", "painting", "flooring", "trash_removal", "rekey_locks",
           "keys_remotes", "appliance", "other_damage", "pest_remediation"}
INCLUSION_KEYWORDS = [
    (r"repair|damage|make ?ready|maint|blind|fixture|light|door|window|drywall|paint|carpet|floor", _DAMAGE),
    (r"make ?ready", {"landscaping_lawn", "trash_removal"}),
    (r"clean", {"cleaning", "carpet_cleaning"}),
    (r"trash|haul", {"trash_removal"}),
    (r"lawn|landscap|yard", {"landscaping_lawn"}),
    (r"rent|lease break|one month", {"rent_in_term", "rent_after_move_out", "lease_break_fee", "reletting_fee"}),
    (r"utilit", {"utilities"}),
    (r"rekey|lock", {"rekey_locks"}),
    (r"coordination", {"maintenance_coordination_fee"}),
]
NO_COVERAGE = re.compile(r"(?:no|not) (?:coverage|covered|eligible)|not approved|not cover|excluding|less\b", re.I)


def _val(m):
    v = float(m.group(1).replace(",", "") + ("." + m.group(2) if m.group(2) else ""))
    return v * 1000 if m.group(3) else v


class Notes:
    def __init__(self, text):
        self.text = str(text or "").strip()
        t = self.text
        self.present = bool(t)
        self.decline = next((name for name, p in DECLINES if p.search(t)), None)
        caps = [v for v in (_val(m) for m in CAP.finditer(t)) if v >= 50]
        self.cap = min(caps) if caps else None
        stated = [v for v in (_val(m) for m in APPROVED.finditer(t)) if v >= 50]
        stated += [v for v in (_val(m) for m in BENEFIT_OF.finditer(t)) if v >= 50]
        self.stated_amount = stated[-1] if stated else None
        self.excluded = set()
        if NO_COVERAGE.search(t):
            for pat, cats in EXCLUSION_KEYWORDS:
                if re.search(pat, t, re.I):
                    self.excluded |= cats
        self.goodwill = bool(re.search(r"goodwill", t, re.I))
        # "Paying amount one month rent" -> payout = monthly rent (361).
        self.pay_one_month_rent = bool(re.search(r"(?:paying|approved|pay)\b[^.]*one month(?:'s)? rent", t, re.I)) \
            and self.stated_amount is None
        # Positive list: "paying cleaning, move out repairs and make ready" -> only those are paid (593).
        self.included = None
        m = re.search(r"(?:paying|covering|we are covering|covered)\s+(?:the\s+)?(?:eligible\s+)?(?:charges of\s+)?(.*?)(?:\.\s|\.$|$)", t, re.I)
        if m and not re.search(r"\d", m.group(1)[:12]):
            inc = set()
            for pat, cats in INCLUSION_KEYWORDS:
                if re.search(pat, m.group(1), re.I):
                    inc |= cats
            self.included = inc or None

    def __bool__(self):
        return self.present
