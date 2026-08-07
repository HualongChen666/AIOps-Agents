'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { navGroups } from '@/lib/nav';
import { logout } from '@/lib/api';

interface UserInfo {
  username: string;
  role: string;
}

export function SideNav() {
  const pathname = usePathname();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    navGroups.forEach((g) => (initial[g.title] = true));
    return initial;
  });

  useEffect(() => {
    try {
      const raw = localStorage.getItem('user');
      if (raw && raw !== 'undefined') {
        const parsed = JSON.parse(raw);
        setUser({ username: parsed.username || '', role: parsed.role || '' });
      }
    } catch {
      setUser(null);
    }
  }, []);

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  const toggle = (title: string) =>
    setExpanded((prev) => ({ ...prev, [title]: !prev[title] }));

  return (
    <aside className="w-72 h-full shrink-0 flex flex-col bg-[var(--color-sidebar)] text-[var(--color-sidebar-text)] border-r border-[var(--dds-slate-70)] shadow-[2px_0_8px_rgba(0,0,0,0.12)]">
      {/* Brand header */}
      <div className="h-16 shrink-0 flex items-center px-6 border-b border-[var(--dds-slate-70)] bg-[var(--dds-slate-90)]">
        <div className="w-8 h-8 rounded-md bg-[var(--dds-blue-60)] flex items-center justify-center text-white font-bold mr-3">
          A
        </div>
        <div>
          <div className="font-semibold text-white text-base leading-tight">AIOps Agent</div>
          <div className="text-[11px] text-[var(--dds-slate-30)]">统一运维控制台</div>
        </div>
      </div>

      {/* Nav groups */}
      <div className="flex-1 overflow-y-auto scrollbar-hide py-4 px-3 space-y-4">
        {navGroups.map((group) => (
          <div key={group.title}>
            <button
              onClick={() => toggle(group.title)}
              className="w-full flex items-center justify-between px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--dds-slate-30)] hover:text-white transition-colors rounded-md hover:bg-[var(--dds-slate-70)]"
            >
              <span>{group.title}</span>
              <span className="text-[10px] opacity-80">{expanded[group.title] ? '▾' : '▸'}</span>
            </button>

            {expanded[group.title] && (
              <nav className="mt-1 ml-1 border-l-2 border-[var(--dds-slate-60)] pl-2 space-y-1">
                {group.items.map((item) =>
                  item.href.startsWith('http') ? (
                    <a
                      key={item.href}
                      href={item.href}
                      target={item.target}
                      rel="noopener noreferrer"
                      className="flex items-center justify-between px-3 py-2 rounded-md text-sm text-[var(--dds-slate-20)] hover:bg-[var(--dds-slate-70)] hover:text-white transition-colors"
                    >
                      <span className="truncate">{item.label}</span>
                      <span className="text-xs opacity-60">↗</span>
                    </a>
                  ) : (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center px-3 py-2 rounded-md text-sm transition-colors border-l-4 -ml-[10px] pl-[18px] ${isActive(item.href)
                        ? 'bg-[var(--dds-slate-70)] text-white border-[var(--dds-blue-60)]'
                        : 'border-transparent text-[var(--dds-slate-20)] hover:bg-[var(--dds-slate-70)] hover:text-white'
                        }`}
                    >
                      {item.label}
                    </Link>
                  )
                )}
              </nav>
            )}
          </div>
        ))}
      </div>

      {/* User / logout */}
      {user && (
        <div className="shrink-0 p-3 border-t border-[var(--dds-slate-70)] bg-[var(--dds-slate-90)]">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-white truncate" title={user.username}>
              {user.username}
              <span className="ml-1 text-[10px] text-[var(--dds-slate-30)]">({user.role})</span>
            </div>
          </div>
          <button
            onClick={async () => { await logout(); }}
            className="w-full px-3 py-1.5 rounded text-xs text-white bg-[var(--dds-red-60)] hover:bg-[var(--dds-red-70)] transition-colors"
          >
            退出登录
          </button>
        </div>
      )}

      {/* Footer status */}
      <div className="shrink-0 p-4 text-[11px] text-[var(--dds-slate-30)] border-t border-[var(--dds-slate-70)] bg-[var(--dds-slate-90)]">
        <div className="flex justify-between mb-1">
          <span>前端门户</span>
          <span className="font-medium text-white">:8000</span>
        </div>
        <div className="flex justify-between">
          <span>后端 API</span>
          <span className="font-medium text-white">:3000</span>
        </div>
      </div>
    </aside>
  );
}
