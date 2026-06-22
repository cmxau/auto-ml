"use client";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FeatureImportanceItem } from "@/lib/api/training";

interface Props {
  data: FeatureImportanceItem[];
}

const COLORS = [
  "#3b82f6", "#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd",
  "#ddd6fe", "#ede9fe", "#f5f3ff", "#fafafa", "#f3f4f6",
];

export function FeatureImportanceChart({ data }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <p className="text-sm text-gray-400 text-center">
          No feature importance data available.
        </p>
      </div>
    );
  }

  const top10 = data.slice(0, 10);
  const chartData = top10.map((item) => ({
    feature:
      item.feature.length > 16
        ? item.feature.slice(0, 14) + "…"
        : item.feature,
    fullFeature: item.feature,
    importance: parseFloat(item.importance.toFixed(4)),
  }));

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="text-sm font-semibold text-gray-800 mb-4">
        Feature Importance
      </h3>
      <ResponsiveContainer width="100%" height={Math.max(180, top10.length * 32)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ left: 16, right: 24 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => v.toFixed(3)}
          />
          <YAxis
            type="category"
            dataKey="feature"
            width={110}
            tick={{ fontSize: 11 }}
          />
          <Tooltip
            formatter={(value, _name, props) => [
              typeof value === "number" ? value.toFixed(4) : value,
              (props.payload as { fullFeature?: string } | undefined)?.fullFeature ?? "Importance",
            ]}
          />
          <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
            {chartData.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
