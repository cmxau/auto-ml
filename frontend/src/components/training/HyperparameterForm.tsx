"use client";

type HParam = {
  key: string;
  label: string;
  type: "number" | "select";
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  default: number | string;
};

const HPARAMS: Record<string, HParam[]> = {
  random_forest: [
    { key: "n_estimators", label: "Trees", type: "number", min: 10, max: 500, step: 10, default: 100 },
    { key: "max_depth", label: "Max depth", type: "number", min: 1, max: 50, step: 1, default: 10 },
    { key: "min_samples_split", label: "Min samples split", type: "number", min: 2, max: 20, step: 1, default: 2 },
  ],
  logistic_regression: [
    { key: "C", label: "Regularisation (C)", type: "number", min: 0.01, max: 100, step: 0.1, default: 1.0 },
    { key: "max_iter", label: "Max iterations", type: "number", min: 100, max: 2000, step: 100, default: 1000 },
  ],
  gradient_boosting: [
    { key: "n_estimators", label: "Estimators", type: "number", min: 10, max: 500, step: 10, default: 100 },
    { key: "learning_rate", label: "Learning rate", type: "number", min: 0.001, max: 1, step: 0.01, default: 0.1 },
    { key: "max_depth", label: "Max depth", type: "number", min: 1, max: 20, step: 1, default: 3 },
  ],
  xgboost: [
    { key: "n_estimators", label: "Estimators", type: "number", min: 10, max: 500, step: 10, default: 100 },
    { key: "learning_rate", label: "Learning rate", type: "number", min: 0.001, max: 1, step: 0.01, default: 0.1 },
    { key: "max_depth", label: "Max depth", type: "number", min: 1, max: 20, step: 1, default: 6 },
  ],
  svm: [
    { key: "C", label: "Regularisation (C)", type: "number", min: 0.01, max: 100, step: 0.1, default: 1.0 },
  ],
  random_forest_regressor: [
    { key: "n_estimators", label: "Trees", type: "number", min: 10, max: 500, step: 10, default: 100 },
    { key: "max_depth", label: "Max depth", type: "number", min: 1, max: 50, step: 1, default: 10 },
  ],
  linear_regression: [],
  gradient_boosting_regressor: [
    { key: "n_estimators", label: "Estimators", type: "number", min: 10, max: 500, step: 10, default: 100 },
    { key: "learning_rate", label: "Learning rate", type: "number", min: 0.001, max: 1, step: 0.01, default: 0.1 },
  ],
  xgboost_regressor: [
    { key: "n_estimators", label: "Estimators", type: "number", min: 10, max: 500, step: 10, default: 100 },
    { key: "learning_rate", label: "Learning rate", type: "number", min: 0.001, max: 1, step: 0.01, default: 0.1 },
  ],
};

interface Props {
  modelType: string;
  value: Record<string, number | string>;
  onChange: (params: Record<string, number | string>) => void;
}

export function HyperparameterForm({ modelType, value, onChange }: Props) {
  const params = HPARAMS[modelType] ?? [];
  if (params.length === 0) return null;

  return (
    <div className="space-y-2">
      <label className="text-xs text-gray-500 block">Hyperparameters</label>
      {params.map((p) => (
        <div key={p.key} className="flex items-center gap-3">
          <label className="text-xs text-gray-600 w-36 shrink-0">{p.label}</label>
          <input
            type="number"
            min={p.min}
            max={p.max}
            step={p.step}
            value={value[p.key] ?? p.default}
            onChange={(e) => onChange({ ...value, [p.key]: Number(e.target.value) })}
            className="w-28 text-xs border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <span className="text-xs text-gray-400">default: {p.default}</span>
        </div>
      ))}
    </div>
  );
}

export function defaultHyperparams(modelType: string): Record<string, number | string> {
  return Object.fromEntries((HPARAMS[modelType] ?? []).map((p) => [p.key, p.default]));
}
