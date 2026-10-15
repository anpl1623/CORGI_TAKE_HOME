import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight } from "lucide-react";
import Verdict from "@/components/Verdict";
import { loadDetail, money, summary } from "@/lib/data";

const MARK: Record<string, [string, string]> = {
  covered: ["+", "in"], partial: ["~", "part"], excluded: ["×", "out"], skip: ["·", "skip"],
};

export default async function Claim({ params }: { params: Promise<{ t: string }> }) {
  const { t } = await params;
  const d = loadDetail(Number(t));
  if (!d) notFound();
  const idx = summary.findIndex((r) => r.t === d.tracking);
  const prev = summary[idx - 1]?.t, next = summary[idx + 1]?.t;
  const decided = d.verdict !== "open";
  const diff = decided && d.actual !== null ? d.payout - d.actual : null;

  return (
    <>
      <section className="sec pad" style={{ paddingBottom: "1rem" }}>
        <div className="sec-h" style={{ marginBottom: "0.6rem" }}>
          <span style={{ display: "flex", gap: "0.8rem" }}>
            <Link href="/lookup" className="lnk">
              ← lookup
            </Link>
          </span>
          <span style={{ display: "flex", gap: "0.8rem" }}>
            {prev && (
              <Link href={`/claim/${prev}`} className="lnk" aria-label="Previous claim">
                <ArrowLeft size={11} style={{ display: "inline" }} /> #{prev}
              </Link>
            )}
            {next && (
              <Link href={`/claim/${next}`} className="lnk" aria-label="Next claim">
                #{next} <ArrowRight size={11} style={{ display: "inline" }} />
              </Link>
            )}
          </span>
        </div>
        <div className="idn__no" style={{ fontSize: "clamp(2rem,6vw,3.2rem)" }}>
          Claim <b>#{d.tracking}</b>
        </div>
        <div className="small mono" style={{ marginTop: "0.4rem" }}>
          {[d.address, d.city, d.state].filter(Boolean).join(", ")} · {d.pm}
        </div>

        <div className="decision">
          <div>
            <div className="decision__k">Engine payout</div>
            <div className="decision__v">{money(d.payout)}</div>
          </div>
          <div>
            <div className="decision__k">Actual ({d.status})</div>
            <div className="decision__s">{decided ? money(d.actual) : "not final"}</div>
          </div>
          <div>
            <div className="decision__k">Verdict</div>
            <div className="decision__s">
              <Verdict v={d.verdict} />
              {diff !== null && Math.abs(diff) > 1 && <span className="small mono" style={{ marginLeft: 8 }}>{diff > 0 ? "+" : ""}{diff.toFixed(2)}</span>}
            </div>
          </div>
          <div>
            <div className="decision__k">Docs-only mode</div>
            <div className="decision__s" style={{ color: "var(--color-ink-2)" }}>{money(d.docs_only_payout)}</div>
          </div>
        </div>
      </section>

      <section className="sec pad">
        <div className="cols cols--3-2">
          <div>
            <h2 className="sec-h">
              Line-by-line adjudication <span>{d.lines.length} charges · {d.mode}</span>
            </h2>
            {d.decline_reason && (
              <div className="errata" style={{ marginBottom: "1rem" }}>
                <span className="errata__tag">Declined</span>
                {d.decline_reason}
                {d.amount_if_not_declined !== undefined && (
                  <span className="small mono"> · would have paid {money(d.amount_if_not_declined)}</span>
                )}
                {d.pre_decline_amount ? <span className="small mono"> · sheet keeps {money(d.pre_decline_amount)} calculated before cancellation</span> : null}
              </div>
            )}
            {d.lines.length === 0 ? (
              <p className="small">
                No line items: {d.basis}
                {d.comment_basis ? ` — ${d.comment_basis}` : ""}.
              </p>
            ) : (
              <div className="scroll-x">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th aria-label="Decision"></th>
                      <th>Charge</th>
                      <th className="num">Billed</th>
                      <th className="num">Paid</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.lines.map((l, i) => {
                      const [m, cls] = MARK[l.decision ?? "skip"] ?? ["?", "skip"];
                      return (
                        <tr key={i} className={l.decision === "excluded" || l.decision === "skip" ? "is-out" : ""}>
                          <td>
                            <span className={`mark mark--${cls}`} aria-label={l.decision}>{m}</span>
                          </td>
                          <td>
                            <span style={{ color: "var(--color-ink)" }}>{l.description}</span>
                            <span className="cell-sub">
                              <span className="mono">{l.category}</span> — {l.reason}
                            </span>
                          </td>
                          <td className="num">{money(l.amount)}</td>
                          <td className="num" style={{ fontWeight: 700 }}>{money(l.paid)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    {d.eligible !== undefined && (
                      <>
                        <tr>
                          <td></td>
                          <td>Eligible charges</td>
                          <td></td>
                          <td className="num">{money(d.eligible)}</td>
                        </tr>
                        {(d.credit_total ?? 0) > 0 && (
                          <tr>
                            <td></td>
                            <td>PM-applied credits</td>
                            <td></td>
                            <td className="num">−{money(d.credit_total)}</td>
                          </tr>
                        )}
                        <tr>
                          <td></td>
                          <td>Capped at ceiling {money(d.ceiling)} ({d.ceiling_source})</td>
                          <td></td>
                          <td className="num" style={{ color: "var(--color-spot)" }}>{money(d.payout)}</td>
                        </tr>
                      </>
                    )}
                  </tfoot>
                </table>
              </div>
            )}
            {d.credits.length > 0 && (
              <p className="small" style={{ marginTop: "0.8rem" }}>
                Credits: {d.credits.map((c) => `${c.description} (${money(c.amount)})`).join("; ")}
              </p>
            )}
          </div>

          <div>
            <h2 className="sec-h">
              Claim facts <span>sheet + documents</span>
            </h2>
            <dl className="spec">
              <dt>Claim date</dt><dd>{d.claim_date} · era {d.era}</dd>
              <dt>Max benefit</dt><dd>{money(d.max_benefit)}</dd>
              <dt>Ceiling used</dt><dd>{money(d.ceiling)} · {d.ceiling_source}</dd>
              <dt>Monthly rent</dt><dd>{money(d.rent)}</dd>
              <dt>Lease</dt><dd>{d.lease_start || "—"} → {d.lease_end || "—"}</dd>
              <dt>Move-out</dt><dd>{d.move_out || "—"} · {d.termination ?? "n/a"}</dd>
              <dt>PM family</dt><dd>{d.pm_family}</dd>
              <dt>Basis</dt><dd>{d.basis}</dd>
              <dt>Confidence</dt><dd>{d.confidence ?? "—"}</dd>
              <dt>Extracted by</dt><dd>{d.source ?? "no extraction"}</dd>
              <dt>Review flags</dt><dd>{d.review_flags.length ? d.review_flags.join(", ") : "none"}</dd>
            </dl>
            {d.note && (
              <div className="notice notice--ok" style={{ marginTop: "1rem" }}>
                <div>
                  <div className="caps" style={{ marginBottom: 4 }}>Adjuster note (PM Explanation)</div>
                  {d.note}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
