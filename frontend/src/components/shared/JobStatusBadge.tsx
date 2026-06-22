import type { Job } from "@/lib/api/jobs";

const STATUS_STYLES: Record<string, string> = {
  queued: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export function JobStatusBadge({ status }: { status: Job["status"] }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        STATUS_STYLES[status] ?? "bg-gray-100 text-gray-700"
      }`}
    >
      {status === "running" && (
        <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
      )}
      {status}
    </span>
  );
}
