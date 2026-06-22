"use client";
import type { CorrelationMatrixData } from "@/lib/api/eda";
import { EdaChartCard } from "./EdaChartCard";

function correlationColor(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 0.8)
    return value > 0 ? "bg-blue-700 text-white" : "bg-red-700 text-white";
  if (abs >= 0.5)
    return value > 0 ? "bg-blue-400 text-white" : "bg-red-400 text-white";
  if (abs >= 0.3)
    return value > 0
      ? "bg-blue-200 text-gray-800"
      : "bg-red-200 text-gray-800";
  return "bg-gray-50 text-gray-600";
}

export function CorrelationMatrix({ data }: { data: CorrelationMatrixData }) {
  const { columns, matrix } = data;

  return (
    <EdaChartCard title="Correlation Matrix">
      <div className="overflow-auto">
        <table className="text-xs border-collapse">
          <thead>
            <tr>
              <th className="w-20 p-1" />
              {columns.map((col) => (
                <th
                  key={col}
                  className="p-1 text-gray-600 font-medium"
                  title={col}
                >
                  <div className="w-16 overflow-hidden text-ellipsis whitespace-nowrap">
                    {col}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={columns[i]}>
                <td
                  className="p-1 text-gray-600 font-medium text-right pr-2 max-w-20 truncate"
                  title={columns[i]}
                >
                  {columns[i]}
                </td>
                {row.map((val, j) => (
                  <td
                    key={j}
                    className={`p-1 text-center w-12 h-10 rounded ${correlationColor(val)}`}
                    title={`${columns[i]} vs ${columns[j]}: ${val.toFixed(3)}`}
                  >
                    {val.toFixed(2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </EdaChartCard>
  );
}
