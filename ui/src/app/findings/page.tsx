const FINDINGS: [string, string, string, string][] = [
  ["Amount of Claim is corrupted", "The column is strictly ascending in tracking-number order while claim dates also ascend — it was sorted on its own, detached from its rows.", "The obvious input is garbage.", "Ignored; claim amounts rebuilt from documents."],
  ["53% of files missing from the first download", "Drive splits large folder zips into ~2 GB parts and scatters each claim's files across them; only one part had been saved (2,718 of 5,775 files).", "Most claims were missing their decisive move-out statement.", "Re-downloaded every part, merged with zip-slip guard and no overwrites, verified folder-by-folder against Drive via API."],
  ["~210 claims have no documents", "Tracking #1018–1235 have no folder on Drive at all (verified via API). Corgi: known Drive issue.", "No itemization exists.", "PM note + LLM read of the comment thread; otherwise pay the ceiling. Reported as its own eval set."],
  ["Comments sheet points at an old sort order", "\"Row N\" references the sheet before it was re-sorted.", "Naive joins attach comments to the wrong claims.", "Re-mapped by content (rents, addresses, dates); comments proved noisy for caps (4/76), so only the PM Explanation drives decisions."],
  ["Declined rows that hold an amount", "#440, 568, 803, 829, 1092, 1168: calculated (sometimes approved), then the PM cancelled, owner waived, tenant paid, or prior carrier — \"cheque has never gone out\". #673 holds note text.", "Looks like a payout; nothing was paid.", "Truth = $0; stored amount kept as a secondary label; engine reports amount_if_not_declined."],
  ["Discretionary top-ups & goodwill", "#1081 \"per Doug, additional 500\"; #475, #433 supplements to Max; goodwill payments.", "Not derivable from documents.", "Approved column is the cumulative total; treated as irreducible noise."],
  ["Sheet errors", "Max Benefit below the paid amount (#540); notes contradicting the payout (#697, #431); sheet rent including add-ons; wrong move-out years.", "Irreducible noise / moves caps.", "Document values preferred over sheet values where both exist."],
];

export default function Findings() {
  return (
    <>
      <section className="sec pad">
        <h1 className="sec-h">Data findings <span>found before any modeling</span></h1>
        <div className="errata">
          <span className="errata__tag">Errata</span>
          The book was acquired, poorly maintained, and full of human error — some of it is simply wrong. These are the issues that change the answer,
          and how each one is handled.
        </div>
      </section>
      <section className="sec pad">
        <div className="scroll-x">
          <table className="tbl">
            <thead><tr><th>Finding</th><th>Evidence</th><th>Impact</th><th>Handling</th></tr></thead>
            <tbody>
              {FINDINGS.map(([f, e, i, h]) => (
                <tr key={f}><td className="cell-key">{f}</td><td>{e}</td><td className="small">{i}</td><td>{h}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
