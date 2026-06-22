"use client";

import { AppShell } from "@/components/layout/AppShell";
import { useProjects, useCreateProject, useDeleteProject } from "@/lib/hooks/useProjects";
import Link from "next/link";
import { useState } from "react";

export default function DashboardPage() {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");

  const handleDelete = (e: React.MouseEvent, id: string, projectName: string) => {
    e.preventDefault();
    if (!confirm(`Delete "${projectName}"? This cannot be undone.`)) return;
    deleteProject.mutate(id);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await createProject.mutateAsync({ name: name.trim() });
    setName("");
    setShowForm(false);
  };

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-gray-900">Projects</h1>
          <button
            onClick={() => setShowForm(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            New project
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleCreate}
            className="mb-6 bg-white border border-gray-200 rounded-xl p-4 flex gap-3"
          >
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Project name"
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={createProject.isPending}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm text-gray-500"
            >
              Cancel
            </button>
          </form>
        )}

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-28 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : projects?.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <p className="text-lg font-medium">No projects yet</p>
            <p className="text-sm mt-1">Create your first project to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {projects?.map((p) => (
              <div
                key={p.id}
                className="relative bg-white border border-gray-200 rounded-xl hover:border-blue-400 hover:shadow-sm transition-all group"
              >
                <Link href={`/projects/${p.id}`} className="block p-5">
                  <h2 className="font-medium text-gray-900 pr-8">{p.name}</h2>
                  {p.description && (
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                      {p.description}
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-3">
                    {new Date(p.created_at).toLocaleDateString()}
                  </p>
                </Link>
                <button
                  onClick={(e) => handleDelete(e, p.id, p.name)}
                  disabled={deleteProject.isPending}
                  className="absolute top-3 right-3 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-30"
                  title="Delete project"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
