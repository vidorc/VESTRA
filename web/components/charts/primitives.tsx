"use client";

/**
 * Recharts primitives themed to the DESIGN.md dark terminal. Each wrapper fixes
 * the chrome (grid, axes, tooltip, colors) so screens pass only data + a couple
 * of keys — keeping every chart visually part of the same system.
 *
 * A ResponsiveContainer needs a sized parent, so each wrapper renders inside a
 * fixed-height box (override via `height`).
 */

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { actionColor, axisTick, chartTokens, gridStroke, seriesColor } from "./theme";

/** Shared dark tooltip: panel surface, hairline border, mono figures. */
function ChartTooltip({
  active,
  payload,
  label,
  valueFormat,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number | string; color?: string }>;
  label?: string | number;
  valueFormat?: (v: number | string) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-sm border border-hairline-strong bg-panel px-sm py-xs shadow-level-3">
      {label != null && label !== "" && (
        <p className="mb-xxs font-mono text-caption uppercase tracking-wide text-mute">{label}</p>
      )}
      {payload.map((p, i) => (
        <div key={i} className="flex items-center gap-xs">
          {p.color && <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />}
          {p.name && <span className="text-caption text-body">{p.name}</span>}
          <span className="ml-auto font-mono text-caption tnum text-ink">
            {valueFormat && p.value != null ? valueFormat(p.value) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export interface Datum {
  [key: string]: string | number;
}

/** Donut — portfolio allocation, sector mix. Slices use the categorical palette. */
export function DonutChart({
  data,
  nameKey,
  valueKey,
  height = 220,
  colorFor,
  valueFormat,
}: {
  data: Datum[];
  nameKey: string;
  valueKey: string;
  height?: number;
  colorFor?: (d: Datum, i: number) => string;
  valueFormat?: (v: number | string) => string;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={2}
            stroke={chartTokens.canvas}
            strokeWidth={2}
          >
            {data.map((d, i) => (
              <Cell key={i} fill={colorFor ? colorFor(d, i) : seriesColor(i)} />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip valueFormat={valueFormat} />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Horizontal/vertical bar — risk factors, per-ticker tallies. */
export function BarSeriesChart({
  data,
  categoryKey,
  valueKey,
  height = 240,
  layout = "horizontal",
  colorFor,
  valueFormat,
}: {
  data: Datum[];
  categoryKey: string;
  valueKey: string;
  height?: number;
  layout?: "horizontal" | "vertical";
  colorFor?: (d: Datum, i: number) => string;
  valueFormat?: (v: number | string) => string;
}) {
  const vertical = layout === "vertical";
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout={layout} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
          <CartesianGrid stroke={gridStroke} horizontal={!vertical} vertical={vertical} />
          {vertical ? (
            <>
              <XAxis type="number" tick={axisTick} stroke={gridStroke} />
              <YAxis type="category" dataKey={categoryKey} tick={axisTick} stroke={gridStroke} width={90} />
            </>
          ) : (
            <>
              <XAxis dataKey={categoryKey} tick={axisTick} stroke={gridStroke} />
              <YAxis tick={axisTick} stroke={gridStroke} />
            </>
          )}
          <Tooltip cursor={{ fill: chartTokens.panel }} content={<ChartTooltip valueFormat={valueFormat} />} />
          <Bar dataKey={valueKey} radius={vertical ? [0, 3, 3, 0] : [3, 3, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={colorFor ? colorFor(d, i) : seriesColor(i)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Line/area — confidence trends, performance over time. */
export function TrendChart({
  data,
  xKey,
  series,
  height = 240,
  area = false,
  yDomain,
  valueFormat,
}: {
  data: Datum[];
  xKey: string;
  series: { key: string; label: string; color?: string }[];
  height?: number;
  area?: boolean;
  yDomain?: [number, number];
  valueFormat?: (v: number | string) => string;
}) {
  const Chart = area ? AreaChart : LineChart;
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <Chart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke={gridStroke} vertical={false} />
          <XAxis dataKey={xKey} tick={axisTick} stroke={gridStroke} />
          <YAxis tick={axisTick} stroke={gridStroke} domain={yDomain} />
          <Tooltip content={<ChartTooltip valueFormat={valueFormat} />} />
          {series.map((s, i) => {
            const color = s.color ?? seriesColor(i);
            return area ? (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={color}
                fill={color}
                fillOpacity={0.12}
                strokeWidth={2}
                dot={false}
              />
            ) : (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={color}
                strokeWidth={2}
                dot={{ r: 2, fill: color }}
                activeDot={{ r: 4 }}
              />
            );
          })}
        </Chart>
      </ResponsiveContainer>
    </div>
  );
}

/** Single-value radial gauge — an alternate to HealthGauge for 0-100 ratios. */
export function RadialGauge({
  value,
  color = chartTokens.up,
  height = 180,
  label,
}: {
  value: number;
  color?: string;
  height?: number;
  label?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          innerRadius="70%"
          outerRadius="100%"
          data={[{ value: pct }]}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar background={{ fill: chartTokens.panel }} dataKey="value" cornerRadius={8} fill={color} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-display-md tnum" style={{ color }}>
          {Math.round(pct)}
        </span>
        {label && <span className="font-mono text-caption uppercase tracking-wide text-mute">{label}</span>}
      </div>
    </div>
  );
}

export { actionColor, chartTokens, seriesColor };
