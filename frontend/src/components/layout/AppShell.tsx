"use client";

import { TopNav } from "./TopNav";
import { SideNav } from "./SideNav";

interface NavItem {
  label: string;
  href: string;
}

export function AppShell({
  children,
  sideNavItems = [],
}: {
  children: React.ReactNode;
  sideNavItems?: NavItem[];
}) {
  return (
    <div className="h-screen flex flex-col">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        {sideNavItems.length > 0 && <SideNav items={sideNavItems} />}
        <main className="flex-1 overflow-auto bg-gray-50 p-6">{children}</main>
      </div>
    </div>
  );
}
