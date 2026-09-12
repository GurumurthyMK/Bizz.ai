"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatBucketLabel } from "@/lib/format";
import type { OverviewTrendBucket } from "@/types";

interface TrendChartsProps {
  trends: OverviewTrendBucket[];
}

type BucketRow = OverviewTrendBucket & { label: string };

function toRows(trends: OverviewTrendBucket[]): BucketRow[] {
  return trends.map((bucket) => ({
    ...bucket,
    label: formatBucketLabel(bucket.period_start),
  }));
}

const axisTick = { fontSize: 12, fill: "hsl(var(--muted-foreground))" } as const;
const tooltipStyle = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "var(--radius)",
  fontSize: 13,
} as const;

/** Screen-reader alternative: every chart ships its data as a table. */
function TrendDataTable({ rows }: { rows: BucketRow[] }) {
  return (
    <table className="sr-only">
      <caption>Business trends by 30-day period</caption>
      <thead>
        <tr>
          <th scope="col">Period</th>
          <th scope="col">Revenue</th>
          <th scope="col">Orders</th>
          <th scope="col">Active customers</th>
          <th scope="col">Interactions</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.period_start}>
            <th scope="row">{row.label}</th>
            <td>{row.revenue}</td>
            <td>{row.orders}</td>
            <td>{row.active_customers}</td>
            <td>{row.interactions}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** How is revenue moving across the last six 30-day periods? */
export function RevenueTrendChart({ trends }: TrendChartsProps) {
  const rows = toRows(trends);
  return (
    <figure className="flex flex-col gap-2 rounded-lg border bg-card p-4">
      <figcaption>
        <h3 className="text-section-title">Revenue trend</h3>
        <p className="text-sm text-muted-foreground">Completed revenue per 30-day period.</p>
      </figcaption>
      <div role="img" aria-label={`Revenue trend across ${rows.length} periods`}>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="label" tick={axisTick} tickLine={false} axisLine={false} />
            <YAxis
              tick={axisTick}
              tickLine={false}
              axisLine={false}
              width={52}
              tickFormatter={(value: number) =>
                value >= 1000 ? `${Math.round(value / 1000)}k` : `${value}`
              }
            />
            <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`$${Number(value).toLocaleString()}`, "Revenue"]} />
            <Line
              type="monotone"
              dataKey="revenue"
              name="Revenue"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <TrendDataTable rows={rows} />
    </figure>
  );
}

/** Is customer activity broadening or narrowing? Orders vs active customers. */
export function ActivityChart({ trends }: TrendChartsProps) {
  const rows = toRows(trends);
  return (
    <figure className="flex flex-col gap-2 rounded-lg border bg-card p-4">
      <figcaption>
        <h3 className="text-section-title">Customer activity</h3>
        <p className="text-sm text-muted-foreground">Orders and active customers per 30-day period.</p>
      </figcaption>
      <div role="img" aria-label={`Customer activity across ${rows.length} periods`}>
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="label" tick={axisTick} tickLine={false} axisLine={false} />
            <YAxis tick={axisTick} tickLine={false} axisLine={false} width={40} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="orders" name="Orders" fill="hsl(var(--primary))" radius={[2, 2, 0, 0]} />
            <Line
              type="monotone"
              dataKey="active_customers"
              name="Active customers"
              stroke="hsl(var(--muted-foreground))"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <TrendDataTable rows={rows} />
    </figure>
  );
}
