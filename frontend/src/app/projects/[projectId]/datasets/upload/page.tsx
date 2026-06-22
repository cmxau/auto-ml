"use client";

import { AppShell } from "@/components/layout/AppShell";
import { DatasetUploadCard } from "@/components/dataset/DatasetUploadCard";
import { useParams } from "next/navigation";

export default function UploadPage() {
  const { projectId } = useParams<{ projectId: string }>();

  const navItems = [
    { label: "Overview", href: `/projects/${projectId}` },
  ];

  return (
    <AppShell sideNavItems={navItems}>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-xl font-semibold text-gray-900 mb-6">
          Upload Dataset
        </h1>
        <DatasetUploadCard projectId={projectId} />
      </div>
    </AppShell>
  );
}
