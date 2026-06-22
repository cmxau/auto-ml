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
import type { HistogramData, BarChartData, Chart } from "@/lib/api/eda";
import { EdaChartCard } from "./EdaChartCard";

function HistogramChart({
  column,
  data,
}: {
  column: string;
  data: HistogramData;
}) {
  const chartData = data.counts.map((count, i) => ({
    bin: `${data.bins[i].toFixed(1)}–${data.bins[i + 1].toFixed(1)}`,
    count,
  }));

  return (
    <EdaChartCard title={`Distribution: ${column}`}>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="bin"
            tick={{ fontSize: 10 }}
            angle={-30}
            textAnchor="end"
            interval={2}
          />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="count" fill="#3b82f6" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </EdaChartCard>
  );
}

function BarChartDisplay({
  column,
  data,
}: {
  column: string;
  data: BarChartData;
}) {
  const chartData = data.labels.map((label, i) => ({
    label,
    count: data.counts[i],
  }));

  return (
    <EdaChartCard title={`Value counts: ${column}`}>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            angle={-30}
            textAnchor="end"
            interval={0}
          />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="count" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </EdaChartCard>
  );
}

export function DistributionChart({ chart }: { chart: Chart }) {
  if (!chart.column) return null;
  if (chart.type === "histogram") {
    return (
      <HistogramChart column={chart.column} data={chart.data as HistogramData} />
    );
  }
  if (chart.type === "bar_chart") {
    return (
      <BarChartDisplay column={chart.column} data={chart.data as BarChartData} />
    );
  }
  return null;
}
