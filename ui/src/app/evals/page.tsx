import { CountBars, PctBars, PredVsActual } from "@/components/Charts";
import { metrics, money0, pct, type Group } from "@/lib/data";

const BASELINE_PAY_MAX = 53.3; // sheet-only: always pay Max Benefit (1,230 decided claims)

function Row({ name, g, note }: { name: string; g?: Group; note?: string }) {
  if (!g) return null;
  return (
    <tr>
      <td className="cell-key">
        {name}
        {note && <span className="cell-sub">{note}</span>}
      </td>
      <td className="num">{g.n.toLocaleString()}</td>
      <td className="num" style={{ fontWeight: 700 }}>{pct(g.exact_pct)}</td>
      <td style={{ width: 120 }}>
        <div className="meter"><i style={{ width: `${g.exact_pct}%` }} /></div>
      </td>
      <td className="num">{pct(g.within_5pct_pct)}</td>
      <td className="num">{pct(g.mape_pct)}</td>
      <td className="num">{money0(g.mae)}</td>
    </tr>
  );
}

function Head({ first }: { first: string }) {
  return (
    <thead>
      <tr>
        <th>{first}</th>
        <th className="num">Claims</th>
        <th className="num">Exact</th>
        <th></th>
        <th className="num">≤ 5%</th>
        <th className="num">MAPE</th>
        <th className="num">MAE</th>
      </tr>
    </thead>
  );
}

export default function Evals() {
  const g = metrics.groups;
  const sets = [
    { name: "Held-out", value: g["set:held-out"].exact_pct },
    { name: "In-sample (tuned on)", value: g["set:in-sample"].exact_pct },
    { name: "Whole book", value: g["all"].exact_pct },
    { name: "No documents on Drive", value: g["set:no documents"].exact_pct },
    { name: "Baseline: pay Max", value: BASELINE_PAY_MAX },
  ];
  const abl = [
    { name: "Baseline: pay Max", value: BASELINE_PAY_MAX },
    { name: "Documents only", value: metrics.ablation["docs-only"].exact_pct },
    { name: "Documents + adjuster notes", value: metrics.ablation["docs + notes"].exact_pct },
  ];
  const eras = ["A", "B", "C", "D"].map((e) => ({ name: { A: "A · 2022", B: "B · Jan–Oct 2023", C: "C · Nov 23–Apr 24", D: "D · Apr 2024 →" }[e]!, value: g[`era:${e}`].exact_pct }));
  const dc = metrics.declines;
  const fams = Object.entries(g).filter(([k, v]) => k.startsWith("family:") && v.n >= 25).sort((a, b) => b[1].n - a[1].n);
  const srcs = Object.entries(g).filter(([k]) => k.startsWith("source:"));

  return (
    <>
      <section className="sec pad">
        <h1 className="sec-h">
          Evals <span>ground truth: Approved Benefit Amount · primary metric: exact match (±$1) · secondary: MAPE</span>
        </h1>
        <p>
          Declined claims are scored as $0 and right/wrong (not in MAPE). Test claims and open claims are excluded. Held-out claims were
          extracted after the rule book was frozen; in-sample claims were used to discover and tune the rules.
        </p>
        <div className="kpis" style={{ marginTop: "1rem" }}>
          <div className="kpi kpi--spot"><div className="kpi__k">Held-out exact</div><div className="kpi__v">{pct(g["set:held-out"].exact_pct)}</div><div className="kpi__c">{g["set:held-out"].n} claims</div></div>
          <div className="kpi"><div className="kpi__k">Held-out MAPE</div><div className="kpi__v">{pct(g["set:held-out"].mape_pct)}</div><div className="kpi__c">median APE {pct(g["set:held-out"].median_ape_pct)}</div></div>
          <div className="kpi"><div className="kpi__k">Book exact</div><div className="kpi__v">{pct(g["all"].exact_pct)}</div><div className="kpi__c">{g["all"].n.toLocaleString()} decided</div></div>
          <div className="kpi"><div className="kpi__k">Decline precision</div><div className="kpi__v">{pct(dc.precision)}</div><div className="kpi__c">recall {pct(dc.recall)}</div></div>
          <div className="kpi"><div className="kpi__k">$ computed vs actual</div><div className="kpi__v">{money0(g["all"].dollar_total_pred)}</div><div className="kpi__c">actual {money0(g["all"].dollar_total_truth)}</div></div>
        </div>
      </section>

      <section className="sec pad">
        <div className="cols cols--2">
          <div>
            <h2 className="sec-h">Exact match by evaluation set <span>red = honest number</span></h2>
            <PctBars data={sets} highlight="Held-out" />
          </div>
          <div>
            <h2 className="sec-h">Ablation <span>extracted claims · what each input adds</span></h2>
            <PctBars data={abl} highlight="Documents + adjuster notes" />
            <p className="small">
              Biggest single finding: adjusters only excluded charges when they wrote a note. Without a note, the PM’s balance was paid up to
              the ceiling.
            </p>
          </div>
        </div>
      </section>

      <section className="sec pad">
        <div className="cols cols--2">
          <div>
            <h2 className="sec-h">Exact match by era <span>claim date</span></h2>
            <PctBars data={eras} />
            <p className="small">Era B (2023) is the noisiest: inconsistent exclusions and management top-ups.</p>
          </div>
          <div>
            <h2 className="sec-h">Error distribution <span>|computed − actual|, decided claims</span></h2>
            <CountBars data={metrics.error_hist} />
          </div>
        </div>
      </section>

      <section className="sec pad">
        <h2 className="sec-h">Computed vs actual <span>each dot a claim · on the diagonal = exact · red = off</span></h2>
        <PredVsActual data={metrics.scatter} />
      </section>

      <section className="sec pad">
        <h2 className="sec-h">Splits <span>exact · within 5% · MAPE · MAE</span></h2>
        <div className="scroll-x">
          <table className="tbl">
            <Head first="Evaluation set" />
            <tbody>
              <Row name="Held-out" g={g["set:held-out"]} note="never used to tune rules" />
              <Row name="In-sample" g={g["set:in-sample"]} note="rule discovery + tuning set" />
              <Row name="No documents on Drive" g={g["set:no documents"]} note="sheet + PM note + LLM comment read" />
              <Row name="Documents, not extracted" g={g["set:documents, not extracted"]} note="decided from notes / hardest note claims" />
              <Row name="Whole book" g={g["all"]} />
            </tbody>
          </table>
        </div>
        <div className="scroll-x" style={{ marginTop: "1.5rem" }}>
          <table className="tbl">
            <Head first="Extractor (model)" />
            <tbody>
              {srcs.map(([k, v]) => (
                <Row key={k} name={k.replace("source:", "")} g={v} note={k.endsWith("haiku-mini") ? "local mini-digest, 10 claims per call" : k.endsWith("none") ? "fallback" : undefined} />
              ))}
            </tbody>
          </table>
        </div>
        <div className="scroll-x" style={{ marginTop: "1.5rem" }}>
          <table className="tbl">
            <Head first="Property manager (n ≥ 25)" />
            <tbody>
              {fams.map(([k, v]) => <Row key={k} name={k.replace("family:", "").replace(/_/g, " ")} g={v} />)}
            </tbody>
          </table>
        </div>
      </section>

      <section className="sec pad">
        <h2 className="sec-h">Declines <span>predicted $0 vs actually declined</span></h2>
        <div className="cols cols--2">
          <table className="tbl" style={{ maxWidth: 420 }}>
            <thead><tr><th></th><th className="num">Actually declined</th><th className="num">Actually paid</th></tr></thead>
            <tbody>
              <tr><td className="cell-key">Engine declined</td><td className="num">{dc.tp}</td><td className="num">{dc.fp}</td></tr>
              <tr><td className="cell-key">Engine paid</td><td className="num">{dc.fn}</td><td className="num">{dc.tn}</td></tr>
            </tbody>
          </table>
          <p className="small">
            Declines with a written reason (note, comment, documents) are caught; declines whose reason never made it into the record cannot be.
            Declined rows that still hold an amount were calculated, then cancelled before payment — scored as $0.
          </p>
        </div>
      </section>
    </>
  );
}
