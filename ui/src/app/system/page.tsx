import { metrics } from "@/lib/data";

const STAGES: [string, string, string, string][] = [
  ["01", "Ingest", "Merge every Drive zip part safely (no overwrites, zip-slip guard). Extract text from PDF / docx / xlsx; flag scans for vision.", "5,775 files → cache/text · 17 s"],
  ["02", "Digest", "Per-claim digest: statements, ledgers, invoices in full; leases cut to rent / term / deposit lines. Mini-digest for cheap mode.", "cache/digest · cache/mini"],
  ["03", "AI extraction", "LLM reads the documents and outputs facts only — 31-category line items, credits, lease & move-out facts, decline flags with quotes. Blind to the outcome.", "cache/extract/T.json · ~1 min/claim, parallel"],
  ["04", "Rules engine", "Deterministic Python adjudicates: declines → ceiling → stated amounts → coverage → credits → caps. Every dollar tied to a rule.", `${(metrics.engine_ms_all_claims / metrics.claims_total).toFixed(2)} ms/claim`],
];

const MODELS: [string, string, string][] = [
  ["Claude Opus (agentic)", "~50k tokens / claim", "Rule discovery + first extractions"],
  ["Gemini Flash", "free tier", "Same schema via a shared prompt (GEMINI_EXTRACTION_PROMPT.md)"],
  ["ChatGPT (Codex)", "plan", "First pass scripted a shortcut → rejected by the quality gate; redo kept (80% exact)"],
  ["Claude Sonnet / Haiku", "cheap", "Note claims (Sonnet), lite claims (Haiku)"],
  ["Haiku, mini-digest", "~12k tokens / claim", "Local pre-trim + 10 claims per call: 88.7% exact vs 71.9% fallback — the production-cost path"],
];

export default function System() {
  return (
    <>
      <section className="sec pad">
        <h1 className="sec-h">System design <span>the AI reads, code decides</span></h1>
        <p>
          The LLM never computes a payout. It turns messy documents into structured facts; a deterministic rule engine makes the decision. That makes
          every payout auditable line by line, rules cheap to change (no document re-reading), the extractor swappable, and adjudication instant.
        </p>
      </section>
      <section className="sec pad">
        <h2 className="sec-h">Pipeline <span>python3 payout.py · ui/ reads exported JSON</span></h2>
        <div className="pipe">
          {STAGES.map(([n, h, p, io]) => (
            <div className="pipe__st" key={n}>
              <div className="pipe__no">STAGE {n}</div>
              <div className="pipe__h">{h}</div>
              <p>{p}</p>
              <div className="pipe__io">{io}</div>
            </div>
          ))}
        </div>
      </section>
      <section className="sec pad">
        <div className="cols cols--2">
          <div>
            <h2 className="sec-h">Adjuster view <span>what a reviewer gets</span></h2>
            <ul className="feat">
              <li>Payout + verdict vs actual, ceiling and its source</li>
              <li>Every charge: covered / excluded / partial, with the rule that applied</li>
              <li>Declines report what the claim would have paid</li>
              <li>Confidence + review flags (flooring without support, mixed pet line, disputes, missing itemization)</li>
              <li>Docs-only vs docs+notes side by side</li>
            </ul>
          </div>
          <div>
            <h2 className="sec-h">Productionizing <span>next steps</span></h2>
            <ul className="feat">
              <li>Auto-approve ceiling-bound, high-confidence claims (~95% exact)</li>
              <li>Route itemized / flagged claims to an adjuster with the breakdown pre-filled</li>
              <li>Codify the implicit rules as explicit policy going forward</li>
              <li>Structured PM itemization template removes most extraction error</li>
              <li>Freeze the 1,200-claim book as a regression suite for rule changes</li>
            </ul>
          </div>
        </div>
      </section>
      <section className="sec pad">
        <h2 className="sec-h">Extraction models <span>same schema, swappable</span></h2>
        <table className="tbl">
          <thead><tr><th>Model / mode</th><th>Cost</th><th>Role &amp; result</th></tr></thead>
          <tbody>
            {MODELS.map(([m, c, r]) => (
              <tr key={m}><td className="cell-key">{m}</td><td className="mono" style={{ whiteSpace: "nowrap" }}>{c}</td><td>{r}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
