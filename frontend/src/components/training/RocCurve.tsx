"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

interface Props {
  fpr: number[];
  tpr: number[];
  auc: number;
}

export function RocCurve({ fpr, tpr, auc }: Props) {
  const data = fpr.map((x, i) => ({
    fpr: Number(x.toFixed(3)),
    tpr: Number(tpr[i].toFixed(3)),
  }));

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="text-sm font-semibold text-gray-800 mb-1">
        ROC Curve{" "}
        <span className="text-blue-600 font-semibold">(AUC = {auc})</span>
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 20, left: 0 }}>
          <XAxis
            dataKey="fpr"
            label={{ value: "FPR", position: "insideBottom", offset: -10 }}
            tick={{ fontSize: 10 }}
          />
          <YAxis
            label={{ value: "TPR", angle: -90, position: "insideLeft", offset: 10 }}
            tick={{ fontSize: 10 }}
          />
          <Tooltip
            formatter={(value) => [
              typeof value === "number" ? value.toFixed(3) : value,
              "TPR",
            ]}
          />
          <ReferenceLine
            segment={[
              { x: 0, y: 0 },
              { x: 1, y: 1 },
            ]}
            stroke="#d1d5db"
            strokeDasharray="4 4"
          />
          <Line
            type="monotone"
            dataKey="tpr"
            stroke="#3b82f6"
            dot={false}
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
