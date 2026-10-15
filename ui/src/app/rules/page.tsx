const STEPS: [string, string, string][] = [
  ["01", "Decline checks → $0", "Adjuster-note phrases (duplicate, not our policy, prior carrier, first-month default, paid in full, payment arrangement, settled with PM, PM cancelled / closed out, owner waived, denied — 47 of 48 hits are true declines). Documents & sheet: test claim, blank Policy #, same address + move-out as an earlier claim, PM void, never moved in, still in possession, short-term lease (≤ 3 mo, from Sep-2024)."],
  ["02", "Ceiling", "Max Benefit from the sheet. An adjuster-stated cap (“cannot exceed $X”) wins — 34/39 exact. Rent cap ⌈rent ÷ 500⌉ × 500 applies only to Treaty T00001 claims dated ≥ 2024-04-24 on terms starting ≥ 2023-07-01 (26/33 binding cases vs 3/76 outside; 134/137 cap notes use the formula)."],
  ["03", "Stated amounts", "“Approved for $X” / “benefit of $X” pays X (6/7). “Paying one month rent” pays the monthly rent. A positive list (“paying cleaning, move out repairs and make ready”) pays only those categories."],
  ["04", "Default practice", "Pay the PM’s open balance, net of PM-applied credits (cash deposit applied, prepaid balance, re-let refund), up to the ceiling. YRIG’s own later tenant settlements are never netted. The flat $200 coordination fee was not paid before Nov-2023."],
  ["05", "Adjuster wrote a note → exclusion rule book", "Apply the category coverage below; move-out month prorated (rent × days ÷ days-in-month); lease-break bucket capped at one month’s rent."],
  ["06", "No documents", "LLM reads the adjuster comment thread (blind to outcome): decline, stated or summed amount, stated cap (≥ 0.5 confidence → 84.7% exact). Otherwise pay the ceiling."],
];

const COVER: [string, string, string][] = [
  ["Covered", "Unpaid rent while in possession (in term), prorated move-out month, cleaning, carpet cleaning, repairs/damage, paint, flooring, trash-out, rekey, keys/remotes, appliances, infestation remediation", "PM billed it; tenant caused it"],
  ["Capped", "Lease-break fee + reletting fee + rent after move-out within term", "≤ 1 × monthly rent (764: 935; 1162: 250)"],
  ["Capped", "Landscaping / lawn", "≤ $500 per claim"],
  ["Capped", "Move-out coordination fee", "≤ $200, PURE (SC) and New Heights only"],
  ["PM deal", "Utilities", "PMS Columbus: full · StarPointe: ≤ $150 from Apr-2024 · everyone else: excluded"],
  ["Paid", "Holdover rent ≤ 3 days through move-out", "393, 952, 935"],
  ["Excluded", "Late, NSF/returned-payment, admin/itemization/convenience, eviction/legal/court, SDRP premiums, RBP/renters-insurance/liability, HOA, collection fees", "Most frequent exclusion notes"],
  ["Excluded", "Pet damage, odor, pet fees", "Pet policy / pet deposit"],
  ["Excluded", "Water, plumbing, fire, flood damage", "Renters / HO policy"],
  ["Excluded", "Rent after lease expiration (holdover > 3 days, month-to-month)", "417, 835, 966"],
  ["Excluded", "Amenity package, lease violation, garage rent, concession repayment, re-inspection, asset protection, routine pest/gutter", "other_fee / pest_routine"],
];

const ERAS: [string, string, string][] = [
  ["A", "before 2023", "Max Benefit almost always (31/33). Gross balance otherwise."],
  ["B", "Jan – Oct 2023", "Gross PM balance incl. fees; caps flagged in comments but not applied; management top-ups."],
  ["C", "Nov 2023 – Apr 2024", "New adjuster: itemized exclusions appear in notes; first-month-default declines from 2023-11-27."],
  ["D", "Apr 2024 →", "Era C + T00001 rent cap enforced, sublimits (landscaping, coordination, StarPointe utilities)."],
];

export default function Rules() {
  return (
    <>
      <section className="sec pad">
        <h1 className="sec-h">Rule book <span>payout_engine/rules.py · engine.py · notes.py</span></h1>
        <p>
          Reverse-engineered from 110 hand-audited claims, every PM Explanation, and the 13k-row Comments sheet, then tested rule-by-rule against the
          whole book. Every number on a claim page is traceable to one of these rows.
        </p>
      </section>
      <section className="sec pad">
        <h2 className="sec-h">Decision procedure <span>evaluated in order</span></h2>
        <table className="tbl">
          <thead><tr><th>Step</th><th>Rule</th><th>Detail &amp; evidence</th></tr></thead>
          <tbody>
            {STEPS.map(([n, h, d]) => (
              <tr key={n}><td className="mono" style={{ color: "var(--color-spot)" }}>{n}</td><td className="cell-key" style={{ whiteSpace: "nowrap" }}>{h}</td><td>{d}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="sec pad">
        <h2 className="sec-h">Category coverage <span>when the adjuster applied exclusions</span></h2>
        <div className="scroll-x">
          <table className="tbl">
            <thead><tr><th>Treatment</th><th>Charges</th><th>Condition / evidence</th></tr></thead>
            <tbody>
              {COVER.map(([t, c, e], i) => (
                <tr key={i}>
                  <td><span className="chip" style={t === "Excluded" ? { color: "var(--color-spot)", borderColor: "var(--color-spot)" } : undefined}>{t}</span></td>
                  <td style={{ color: "var(--color-ink)" }}>{c}</td>
                  <td className="small">{e}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="sec pad">
        <h2 className="sec-h">Eras <span>adjudication practice changed over time</span></h2>
        <table className="tbl">
          <thead><tr><th>Era</th><th>Claim dates</th><th>Practice</th></tr></thead>
          <tbody>
            {ERAS.map(([e, d, p]) => (
              <tr key={e}><td className="mono cell-key">{e}</td><td className="mono" style={{ whiteSpace: "nowrap" }}>{d}</td><td>{p}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
