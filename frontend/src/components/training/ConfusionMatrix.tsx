"use client";

interface Props {
  matrix: number[][];
  classes: string[];
}

export function ConfusionMatrix({ matrix, classes }: Props) {
  const max = Math.max(...matrix.flat());
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="text-sm font-semibold text-gray-800 mb-4">Confusion Matrix</h3>
      <div className="overflow-auto">
        <table className="text-xs border-collapse">
          <thead>
            <tr>
              <th className="p-1 text-gray-400"></th>
              {classes.map((c) => (
                <th key={c} className="p-2 text-center text-gray-500 font-normal">
                  Pred: {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={i}>
                <td className="p-2 text-gray-500 font-normal whitespace-nowrap">
                  Act: {classes[i]}
                </td>
                {row.map((val, j) => (
                  <td
                    key={j}
                    className="p-3 text-center font-semibold rounded"
                    style={{
                      backgroundColor:
                        i === j
                          ? `rgba(34,197,94,${0.2 + 0.6 * (val / (max || 1))})`
                          : `rgba(239,68,68,${0.1 + 0.5 * (val / (max || 1))})`,
                      color: i === j ? "#166534" : "#991b1b",
                    }}
                  >
                    {val}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
