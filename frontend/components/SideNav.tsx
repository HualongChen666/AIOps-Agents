'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { navGroups } from '@/lib/nav';

export function SideNav() {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    navGroups.forEach((g) => (initial[g.title] = true));
    return initial;
  });

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  const toggle = (title: string) =>
    setExpanded((prev) => ({ ...prev, [title]: !prev[title] }));

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-gray-900 text-gray-100 border-r border-gray-800 flex flex-col z-50">
      <div className="h-14 flex items-center px-4 border-b border-gray-800 font-bold text-lg tracking-wide">
        AIOps Agent
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {navGroups.map((group) => (
          <div key={group.title}>
            <button
              onClick={() => toggle(group.title)}
              className="w-full flex items-center justify-between px-2 py-2 text-xs font-semibold uppercase tracking-wider text-gray-400 hover:text-white transition"
            >
              <span>{group.title}</span>
              <span className="text-[10px]">{expanded[group.title] ? '▾' : '▸'}</span>
            </button>
            {expanded[group.title] && (
              <div className="mt-1 space-y-1">
                {group.items.map((item) =>
                  item.href.startsWith('http') ? (
                    <a
                      key={item.href}
                      href={item.href}
                      target={item.target}
                      className="block px-3 py-2 rounded-md text-sm hover:bg-gray-800 transition text-gray-300 hover:text-white"
                    >
                      {item.label} ↗
                    </a>
                  ) : (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`block px-3 py-2 rounded-md text-sm transition ${
                        isActive(item.href)
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                      }`}
                    >
                      {item.label}
                    </Link>
                  )
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="p-3 text-xs text-gray-500 border-t border-gray-800">
        前端: 3000 | 后端: 8000
      </div>
    </aside>
  );
}
