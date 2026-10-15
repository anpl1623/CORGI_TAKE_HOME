"use client";

import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
  ReferenceLine, ZAxis,
} from "recharts";

const INK = "#111214", INK3 = "#6B7178", HAIR = "#E3E4E1", SPOT = "#C81E16";
const AXIS = { fontFamily: "Roboto Mono, monospace", fontSize: 10, fill: INK3 };
const TIP = {
  contentStyle: { borderRadius: 0, border: `1.5px solid ${INK}`, fontFamily: "Roboto Mono, monospace", fontSize: 11, boxShadow: "none" },
  cursor: { fill: "#F7F7F4" },
};

export function PctBars({ data, highlight }: { data: { name: string; value: number; sub?: string }[]; highlight?: string }) {
  return (
    <div className="chart-box" style={{ height: Math.max(160, data.length * 42 + 30) }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 52, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} stroke={HAIR} />
          <XAxis type="number" domain={[0, 100]} tick={AXIS} tickFormatter={(v) => `${v}%`} stroke={HAIR} />
          <YAxis type="category" dataKey="name" width={170} tick={{ ...AXIS, fill: INK, fontSize: 11 }} stroke={HAIR} />
          <Tooltip {...TIP} formatter={(v: number) => [`${v.toFixed(1)}%`, "exact match"]} />
          <Bar dataKey="value" barSize={16} isAnimationActive={false}>
            {data.map((d) => (
              <Cell key={d.name} fill={d.name === highlight ? SPOT : INK} />
            ))}
            <LabelList dataKey="value" position="right" formatter={(v: number) => `${v.toFixed(1)}%`} style={{ ...AXIS, fill: INK, fontSize: 11 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CountBars({ data }: { data: { bin: string; n: number }[] }) {
  return (
    <div className="chart-box">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 16, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid vertical={false} stroke={HAIR} />
          <XAxis dataKey="bin" tick={AXIS} stroke={HAIR} interval={0} />
          <YAxis tick={AXIS} stroke={HAIR} width={36} />
          <Tooltip {...TIP} formatter={(v: number) => [v, "claims"]} />
          <Bar dataKey="n" isAnimationActive={false}>
            {data.map((d, i) => (
              <Cell key={d.bin} fill={i === 0 ? INK : i >= 4 ? SPOT : INK3} />
            ))}
            <LabelList dataKey="n" position="top" style={{ ...AXIS, fill: INK }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PredVsActual({ data }: { data: { t: number; actual: number; payout: number; verdict: string }[] }) {
  const ok = data.filter((d) => d.verdict === "exact"), off = data.filter((d) => d.verdict !== "exact");
  return (
    <div className="chart-box" style={{ height: 340 }}>
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 8, right: 16, bottom: 18, left: 8 }}>
          <CartesianGrid stroke={HAIR} />
          <XAxis type="number" dataKey="actual" name="Actual" tick={AXIS} stroke={HAIR} tickFormatter={(v) => `$${v / 1000}k`}
            label={{ value: "actual approved", position: "insideBottom", offset: -10, style: AXIS }} />
          <YAxis type="number" dataKey="payout" name="Computed" tick={AXIS} stroke={HAIR} width={44} tickFormatter={(v) => `$${v / 1000}k`} />
          <ZAxis range={[14, 14]} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 6000, y: 6000 }]} stroke={INK3} strokeDasharray="3 3" />
          <Tooltip {...TIP} cursor={{ strokeDasharray: "3 3" }}
            formatter={(v: number, n: string) => [`$${v.toLocaleString()}`, n]}
            labelFormatter={() => ""} />
          <Scatter name="exact" data={ok} fill={INK} fillOpacity={0.55} isAnimationActive={false} />
          <Scatter name="off" data={off} fill={SPOT} fillOpacity={0.75} isAnimationActive={false} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
