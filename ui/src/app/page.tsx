import Link from "next/link";
import LookupBar from "@/components/LookupBar";
import { metrics, money0, pct } from "@/lib/data";

export default function Home() {
  const g = metrics.groups;
  const all = g["all"], held = g["set:held-out"], ins = g["set:in-sample"];
  const perClaimMs = metrics.engine_ms_all_claims / metrics.claims_total;

  return (
    <>
      <section className="idn pad">
        <div className="idn__no settle">
          CLM-<b>2026</b>
        </div>
        <h1 className="idn__sub settle settle-1">
          Security-deposit claim payouts, reverse-engineered from {metrics.claims_total.toLocaleString()} historical claims.
        </h1>
        <div className="idn__meta settle settle-2">
          <span className="chip">SDRP claims · YRIG book 2022–2025</span>
          <span className="chip">{metrics.extracted} claims AI-extracted</span>
          <span className="chip">5,775 source documents</span>
          <span className="chip">deterministic rule engine</span>
        </div>
      </section>

      <section className="sec pad">
        <h2 className="sec-h">
          Measured performance <span>vs. Approved Benefit Amount · exact = within $1</span>
        </h2>
        <div className="kpis">
          <div className="kpi kpi--spot">
            <div className="kpi__k">Exact match · whole book</div>
            <div className="kpi__v">{pct(all.exact_pct)}</div>
            <div className="kpi__c">{all.n.toLocaleString()} decided claims, every method</div>
          </div>
          <div className="kpi">
            <div className="kpi__k">Exact · held-out</div>
            <div className="kpi__v">{pct(held.exact_pct)}</div>
            <div className="kpi__c">{held.n} claims never used to tune rules</div>
          </div>
          <div className="kpi">
            <div className="kpi__k">MAPE · held-out</div>
            <div className="kpi__v">{pct(held.mape_pct)}</div>
            <div className="kpi__c">mean abs. % error, paid claims</div>
          </div>
          <div className="kpi">
            <div className="kpi__k">Within 5% · book</div>
            <div className="kpi__v">{pct(all.within_5pct_pct)}</div>
            <div className="kpi__c">MAPE {pct(all.mape_pct)} · MAE {money0(all.mae)}</div>
          </div>
          <div className="kpi">
            <div className="kpi__k">Meeting examples</div>
            <div className="kpi__v">
              15/15<small>exact</small>
            </div>
            <div className="kpi__c">#7–20 and #49</div>
          </div>
          <div className="kpi">
            <div className="kpi__k">Engine speed</div>
            <div className="kpi__v">
              {perClaimMs.toFixed(2)}
              <small>ms / claim</small>
            </div>
            <div className="kpi__c">whole book in {Math.round(metrics.engine_ms_all_claims)} ms</div>
          </div>
        </div>
        <p className="small" style={{ marginTop: "0.7rem" }}>
          In-sample (rules tuned on these) {pct(ins.exact_pct)} exact. Baseline “always pay Max Benefit”: 53.3% exact.
        </p>
      </section>

      <section className="sec pad">
        <h2 className="sec-h">
          Payout lookup <span>single claim · range · list</span>
        </h2>
        <LookupBar />
      </section>

      <section className="sec pad">
        <h2 className="sec-h">
          What was asked → where it lives <span>kickoff call, 10/15</span>
        </h2>
        <div className="scroll-x">
          <table className="tbl">
            <thead>
              <tr>
                <th>Ask</th>
                <th>Delivered</th>
                <th>Page</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["“Give us 49, or 7 to 20, and get the claim payout”", "Lookup by number, range or list; adjuster breakdown per claim", "/lookup"],
                ["Rule set: what is covered, in what cases, what makes the payout", "Decision procedure, coverage by category, caps, declines — each with evidence counts", "/rules"],
                ["Evals against the Approved Benefit Amount", "Exact %, MAPE (per Cooper), held-out vs in-sample, ablations, error distribution", "/evals"],
                ["Messy data, human error, exceptions", "Corrupted columns, missing files, declined-with-amount rows, irreducible noise", "/findings"],
                ["Speed + a thoughtful system, adjuster view", "AI extracts facts, code decides; ms per claim; review flags + confidence", "/system"],
              ].map(([a, d, h]) => (
                <tr key={h}>
                  <td className="cell-key">{a}</td>
                  <td>{d}</td>
                  <td>
                    <Link className="rowlink" href={h}>
                      {h}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="sec pad">
        <h2 className="sec-h">
          How a payout is decided <span>engine.compute(), in order</span>
        </h2>
        <ol className="feat" style={{ counterReset: "x" }}>
          <li>Decline checks — adjuster note phrases (47/48 precise), blank policy, duplicate, test claim, PM cancelled, tenant paid the PM.</li>
          <li>Ceiling — Max Benefit; an adjuster-stated cap wins; rent cap ⌈rent/500⌉×500 for T00001 from Apr-2024.</li>
          <li>Stated amounts — “approved for $X”, “paying one month rent”.</li>
          <li>Default practice — pay the PM’s open balance (net of PM-applied credits) up to the ceiling.</li>
          <li>Adjuster wrote a note → apply the exclusion rule book (fees, pet, water, holdover; lease-break ≤ 1 month rent).</li>
          <li>No documents → LLM read of the comment thread, else pay the ceiling.</li>
        </ol>
      </section>
    </>
  );
}
