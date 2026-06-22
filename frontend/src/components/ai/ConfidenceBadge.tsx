interface Props {
  score: number | null;
}

export function ConfidenceBadge({ score }: Props) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const color =
    pct >= 80
      ? "bg-green-100 text-green-800"
      : pct >= 60
      ? "bg-yellow-100 text-yellow-800"
      : "bg-red-100 text-red-800";
  return (
    <span
      className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${color}`}
    >
      {pct}% confidence
    </span>
  );
}
