export function EdaChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-4">{title}</h3>
      {children}
    </div>
  );
}
