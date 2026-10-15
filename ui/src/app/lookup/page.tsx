import Link from "next/link";
import LookupBar from "@/components/LookupBar";
import Verdict from "@/components/Verdict";
import { byId, money, parseSelection, pct, summarize } from "@/lib/data";

export default async function Lookup({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q = "" } = await searchParams;
  const t0 = performance.now();
  const ids = parseSelection(q);
  const rows = ids.map((t) => byId.get(t)!);
  const s = summarize(rows);
  const ms = performance.now() - t0;

  return (
    <>
      <section className="sec pad">
        <h1 className="sec-h">
          Payout lookup <span>tracking number · range · list · “open” · “all”</span>
        </h1>
        <LookupBar value={q} />
      </section>

      {q && (
        <section className="sec pad">
          <h2 className="sec-h">
            {rows.length ? `${rows.length} claim${rows.length > 1 ? "s" : ""}` : "No matching tracking numbers"}
            <span>computed in {ms.toFixed(1)} ms</span>
          </h2>
          {rows.length > 0 && (
            <>
              <div className="kpis" style={{ marginBottom: "1.1rem" }}>
                <div className="kpi">
                  <div className="kpi__k">Scored</div>
                  <div className="kpi__v">{s.n}</div>
                  <div className="kpi__c">decided claims in selection</div>
                </div>
                <div className="kpi kpi--spot">
                  <div className="kpi__k">Exact match</div>
                  <div className="kpi__v">{s.n ? pct(s.exactPct) : "—"}</div>
                  <div className="kpi__c">{s.exact} of {s.n} within $1</div>
                </div>
                <div className="kpi">
                  <div className="kpi__k">MAPE</div>
                  <div className="kpi__v">{pct(s.mape)}</div>
                  <div className="kpi__c">paid claims</div>
                </div>
                <div className="kpi">
                  <div className="kpi__k">$ computed / actual</div>
                  <div className="kpi__v">{money(s.pred)}</div>
                  <div className="kpi__c">actual {money(s.truth)}</div>
                </div>
              </div>
              <div className="scroll-x">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Status</th>
                      <th className="num">Computed</th>
                      <th className="num">Actual</th>
                      <th className="num">Diff</th>
                      <th>Verdict</th>
                      <th>Basis / reason</th>
                      <th>Era</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.t}>
                        <td>
                          <Link className="rowlink" href={`/claim/${r.t}`}>
                            {r.t}
                          </Link>
                        </td>
                        <td>{r.status}</td>
                        <td className="num" style={{ fontWeight: 700 }}>{money(r.payout)}</td>
                        <td className="num">{r.verdict === "open" ? "—" : money(r.actual)}</td>
                        <td className="num">{r.actual === null || r.verdict === "open" ? "" : (r.payout - r.actual >= 0 ? "+" : "") + (r.payout - r.actual).toFixed(2)}</td>
                        <td>
                          <Verdict v={r.verdict} />
                        </td>
                        <td style={{ maxWidth: 360 }}>{r.decline ?? r.basis}</td>
                        <td className="mono" style={{ fontSize: 11 }}>{r.era}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
    </>
  );
}
