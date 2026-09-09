'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { getNavGroups } from '@/lib/nav';
import { logout } from '@/lib/api';
import { useI18n, useLocale } from '@/lib/i18n';

interface UserInfo {
  username: string;
  role: string;
}

export function isPathActive(currentPath: string, href: string) {
  try {
    const normalize = (p: string) => (p || '').replace(/\/+$, '') || '/';
    const cur = normalize(currentPath);
    const target = normalize(href);
    if (target === '/') return cur === '/';
    if (cur === target) return true;
    return cur.startsWith(target + '/');
  } catch {
    return currentPath === href;
  }
}

export function SideNav() {
  const pathname = usePathname();
  const { locale } = useLocale();
  const t = useI18n();
  const navGroups = useMemo(() => getNavGroups(locale), [locale]);

  const [user, setUser] = useState<UserInfo | null>(null);

  // 初始化 expanded：优先恢复 localStorage；无历史则只展开第一个分组
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    try {
      const raw = typeof window !== 'undefined' ? localStorage.getItem('sidenav_expanded') : null;
      if (raw) return JSON.parse(raw);
    } catch {}
    const initial: Record<string, boolean> = {};
    navGroups.forEach((g, i) => (initial[g.title] = i === 0));
    return initial;
  });

  // 当 navGroups 更新时确保 expanded 包含新组键（保留已有值）
  useEffect(() => {
    setExpanded((prev) => {
      const next: Record<string, boolean> = {};
      navGroups.forEach((g, i) => {
        next[g.title] = typeof prev[g.title] === 'boolean' ? prev[g.title] : i === 0;
      });
      return next;
    });
  }, [navGroups]);

  // 将折叠状态保存在 localStorage
  useEffect(() => {
    try {
      localStorage.setItem('sidenav_expanded', JSON.stringify(expanded));
    } catch {}
  }, [expanded]);

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

  const isActive = (href: string) => isPathActive(pathname || '/', href);

  const toggle = (title: string) =>
    setExpanded((prev) => ({ ...prev, [title]: !prev[title] }));

  return (
    <aside className="w-72 h-full shrink-0 flex flex-col bg-[var(--color-sidebar)] text-[var(--color-sidebar-text)] border-r border-[var(--dds-slate-70)] shadow-[2px_0_8px_rgba(0,0,0,0.12)]">
      <div className="flex-1 overflow-y-auto scrollbar-hide py-4 px-3 space-y-4">
        {navGroups.map((group) => (
          <div key={group.title}>
            <button
              onClick={() => toggle(group.title)}
              className="w-full flex items-center justify-between px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--dds-slate-30)] hover:text-white transition-colors rounded"
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
            {t('sidenav.logout')}
          </button>
        </div>
      )}
    </aside>
  );
}
