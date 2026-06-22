"use client";

import Link from "next/link";
import { useAuthStore } from "@/lib/store/authStore";
import { useLogout } from "@/lib/hooks/useAuth";

export function TopNav() {
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();

  return (
    <header className="h-14 border-b border-gray-200 bg-white flex items-center justify-between px-6 shrink-0">
      <Link href="/dashboard">
        <span className="font-bold text-blue-600 text-lg">AutoML</span>
      </Link>
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">{user?.email}</span>
        <button
          onClick={logout}
          className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
