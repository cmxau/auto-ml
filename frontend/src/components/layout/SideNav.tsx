"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  label: string;
  href: string;
}

export function SideNav({ items }: { items: NavItem[] }) {
  const pathname = usePathname();

  return (
    <nav className="w-56 border-r border-gray-200 bg-white h-full p-4 shrink-0">
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                pathname === item.href || pathname.startsWith(item.href + "/")
                  ? "bg-blue-50 text-blue-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
