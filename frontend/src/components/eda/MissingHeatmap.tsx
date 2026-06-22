"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MissingHeatmapItem } from "@/lib/api/eda";
import { EdaChartCard } from "./EdaChartCard";

export function MissingHeatmap({ data }: { data: MissingHeatmapItem[] }) {
  const chartData = data
    .filter((d) => d.missing_count > 0)
    .map((d) => ({ name: d.column, missing: d.missing_pct }));

  if (chartData.length === 0) {
    return (
      <EdaChartCard title="Missing Values">
        <p className="text-sm text-gray-400 text-center py-4">
          No missing values detected.
        </p>
      </EdaChartCard>
    );
  }

  return (
    <EdaChartCard title="Missing Values (% per column)">
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={100}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(v) => [`${Number(v).toFixed(1)}%`, "Missing"]}
          />
          <Bar dataKey="missing" fill="#f97316" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </EdaChartCard>
  );
}
