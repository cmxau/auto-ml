"use client";
import { useQuery } from "@tanstack/react-query";
import { jobsApi } from "../api/jobs";

export function useJobPoller(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: async () => (await jobsApi.get(jobId!)).data.data,
    enabled: !!jobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "queued" || s === "running" ? 2000 : false;
    },
  });
}
