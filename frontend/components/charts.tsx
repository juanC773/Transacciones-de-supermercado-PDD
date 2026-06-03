"use client";

import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, Legend, ZAxis,
} from "recharts";
import { fmt, fmtCompact } from "@/lib/format";
import type { BoxPlotStat } from "@/lib/types";

const COLORS = ["#2563EB", "#0F766E", "#EA580C", "#7C3AED", "#16A34A", "#DB2777", "#0891B2", "#CA8A04", "#9333EA", "#0EA5E9"];

function TooltipBox({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white shadow-lg">
      <p className="font-medium">{label}</p>
      <p className="tabular-nums">{fmt(payload[0].value)}</p>
    </div>
  );
}

export function HorizontalBars({
  data, dataKey, nameKey, color = "#2563EB", height = 320,
}: { data: Record<string, unknown>[]; dataKey: string; nameKey: string; color?: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="#E2E8F0" />
        <XAxis type="number" tickFormatter={fmtCompact} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey={nameKey} width={130} tick={{ fontSize: 11, fill: "#334155" }} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipBox />} cursor={{ fill: "#F1F5F9" }} />
        <Bar dataKey={dataKey} fill={color} radius={[0, 6, 6, 0]} maxBarSize={22} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function VerticalBars({
  data, dataKey, nameKey, color = "#EA580C", height = 320,
}: { data: Record<string, unknown>[]; dataKey: string; nameKey: string; color?: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ left: 8, right: 8, top: 4, bottom: 40 }}>
        <CartesianGrid vertical={false} stroke="#E2E8F0" />
        <XAxis dataKey={nameKey} tick={{ fontSize: 10, fill: "#64748B" }} angle={-40} textAnchor="end" axisLine={false} tickLine={false} interval={0} />
        <YAxis tickFormatter={fmtCompact} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipBox />} cursor={{ fill: "#F1F5F9" }} />
        <Bar dataKey={dataKey} fill={color} radius={[6, 6, 0, 0]} maxBarSize={32} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function DonutTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { name: string; value: number; payload: { nombre_categoria: string; unidades: number; pct: number } }[];
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white shadow-lg max-w-[220px]">
      <p className="font-medium leading-snug">{row.nombre_categoria}</p>
      <p className="tabular-nums mt-1">{fmt(row.unidades)} unidades</p>
      <p className="tabular-nums text-slate-300">{row.pct.toFixed(1)}% del total mostrado</p>
    </div>
  );
}

/** Participación relativa (top categorías). Etiquetas en % porque los valores absolutos son muy parecidos. */
export function Donut({ data, height = 360 }: { data: { nombre_categoria: string; unidades: number }[]; height?: number }) {
  const total = data.reduce((s, d) => s + d.unidades, 0);
  const enriched = data.map((d) => ({
    ...d,
    pct: total > 0 ? (d.unidades / total) * 100 : 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart margin={{ top: 8, bottom: 8 }}>
        <Pie
          data={enriched}
          dataKey="unidades"
          nameKey="nombre_categoria"
          innerRadius={68}
          outerRadius={108}
          paddingAngle={2}
          stroke="#fff"
          strokeWidth={2}
          label={({ percent }) => (percent >= 0.06 ? `${(percent * 100).toFixed(0)}%` : "")}
          labelLine={false}
        >
          {enriched.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<DonutTooltip />} />
        <Legend verticalAlign="bottom" iconType="circle" wrapperStyle={{ fontSize: 10, paddingTop: 8 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function TimeArea({
  data, dataKey, nameKey, height = 340,
}: { data: Record<string, unknown>[]; dataKey: string; nameKey: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2563EB" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#2563EB" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="#E2E8F0" />
        <XAxis dataKey={nameKey} tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} minTickGap={30} />
        <YAxis tickFormatter={fmtCompact} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipBox />} cursor={{ stroke: "#2563EB", strokeWidth: 1 }} />
        <Area type="monotone" dataKey={dataKey} stroke="#2563EB" strokeWidth={2} fill="url(#areaFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Boxplot apilado en Recharts; data viene precalculada desde la API (min, q1, mediana, q3, max). */
export function BoxPlot({ data, height = 360 }: { data: BoxPlotStat[]; height?: number }) {
  const enriched = data.map((s) => ({
    name: s.name,
    lowBase: s.min,
    minToQ1: s.q1 - s.min,
    q1ToMedian: s.median - s.q1,
    medianToQ3: s.q3 - s.median,
    q3ToMax: s.max - s.q3,
    min: s.min,
    q1: s.q1,
    median: s.median,
    q3: s.q3,
    max: s.max,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={enriched} margin={{ left: 8, right: 8, top: 4, bottom: 60 }}>
        <CartesianGrid vertical={false} stroke="#E2E8F0" />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748B" }} angle={-40} textAnchor="end" axisLine={false} tickLine={false} interval={0} />
        <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
        <Tooltip
          cursor={{ fill: "#F1F5F9" }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const p = payload[0].payload as { name: string; min: number; q1: number; median: number; q3: number; max: number };
            return (
              <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white">
                <p className="mb-1 font-medium">{p.name}</p>
                <p>Mín: {p.min.toFixed(1)} · Q1: {p.q1.toFixed(1)}</p>
                <p>Med: {p.median.toFixed(1)} · Q3: {p.q3.toFixed(1)} · Máx: {p.max.toFixed(1)}</p>
              </div>
            );
          }}
        />
        <Bar dataKey="lowBase" stackId="a" fill="transparent" />
        <Bar dataKey="minToQ1" stackId="a" fill="#CBD5E1" maxBarSize={2} />
        <Bar dataKey="q1ToMedian" stackId="a" fill="#2563EB" maxBarSize={28} />
        <Bar dataKey="medianToQ3" stackId="a" fill="#60A5FA" maxBarSize={28} />
        <Bar dataKey="q3ToMax" stackId="a" fill="#CBD5E1" maxBarSize={2} />
      </BarChart>
    </ResponsiveContainer>
  );
}

const CLUSTER_COLORS = ["#2563EB", "#0F766E", "#EA580C", "#7C3AED"];

export function ClusterScatter({
  points,
  height = 360,
}: {
  points: { pc1: number; pc2: number; cluster_id: number; id_cliente: number }[];
  height?: number;
}) {
  const byCluster = [0, 1, 2, 3].map((cid) => ({
    cluster_id: cid,
    data: points.filter((p) => p.cluster_id === cid),
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ left: 12, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid stroke="#E2E8F0" />
        <XAxis type="number" dataKey="pc1" name="PC1" tick={{ fontSize: 11, fill: "#64748B" }} />
        <YAxis type="number" dataKey="pc2" name="PC2" tick={{ fontSize: 11, fill: "#64748B" }} />
        <ZAxis range={[40, 40]} />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const p = payload[0].payload as { id_cliente: number; cluster_id: number };
            return (
              <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white">
                <p>Cliente {p.id_cliente}</p>
                <p>Cluster {p.cluster_id}</p>
              </div>
            );
          }}
        />
        <Legend />
        {byCluster.map((g) => (
          <Scatter
            key={g.cluster_id}
            name={`Cluster ${g.cluster_id}`}
            data={g.data}
            fill={CLUSTER_COLORS[g.cluster_id % CLUSTER_COLORS.length]}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function Heatmap({
  rows, cols, matrix, diverging = false,
}: { rows: string[]; cols: string[]; matrix: number[][]; diverging?: boolean }) {
  const flat = matrix.flat();
  const max = Math.max(...flat, 1);
  const min = Math.min(...flat, 0);

  function color(v: number) {
    if (diverging) {
      if (v >= 0) return `rgba(37, 99, 235, ${0.15 + Math.min(1, v) * 0.75})`;
      return `rgba(234, 88, 12, ${0.15 + Math.min(1, -v) * 0.75})`;
    }
    const t = (v - min) / (max - min || 1);
    return `rgba(37, 99, 235, ${0.1 + t * 0.85})`;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate" style={{ borderSpacing: 4 }}>
        <thead>
          <tr>
            <th />
            {cols.map((c) => (
              <th key={c} className="px-2 text-xs font-medium text-muted">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r}>
              <td className="whitespace-nowrap pr-3 text-right text-xs font-medium text-muted">{r}</td>
              {cols.map((c, j) => {
                const v = matrix[i]?.[j] ?? 0;
                const light = diverging ? Math.abs(v) > 0.55 : (v - min) / (max - min || 1) > 0.55;
                return (
                  <td
                    key={c}
                    className="h-12 min-w-[60px] rounded-md text-center text-xs font-semibold tabular-nums"
                    style={{ backgroundColor: color(v), color: light ? "#fff" : "#1E293B" }}
                  >
                    {diverging ? v.toFixed(2) : fmt(v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
