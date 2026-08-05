'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { navGroups } from '@/lib/nav';

export default function Home() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading');

  useEffect(() => {
    api
      .get('/api/v1/health/ping')
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'));
  }, []);

  const statusBadge =
    status === 'loading' ? (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-[var(--dds-yellow-10)] text-[var(--dds-yellow-70)]">
        <span className="w-2 h-2 rounded-full bg-[var(--dds-yellow-60)] mr-2 animate-pulse" />
        检测中
      </span>
    ) : status === 'ok' ? (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-[var(--dds-green-10)] text-[var(--dds-green-70)]">
        <span className="w-2 h-2 rounded-full bg-[var(--dds-green-60)] mr-2" />
        后端正常
      </span>
    ) : (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-[var(--dds-red-10)] text-[var(--dds-red-70)]">
        <span className="w-2 h-2 rounded-full bg-[var(--dds-red-60)] mr-2" />
        后端不可用
      </span>
    );

  return (
    <div className="space-y-8">
      {/* Hero header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-[var(--dds-gray-30)]">
        <div>
          <h1 className="text-3xl font-bold text-[var(--dds-slate-90)] mb-1">AIOps Agent 统一控制台</h1>
          <p className="text-[var(--dds-gray-70)] text-sm">企业级 AI 运维监控平台 · 全部功能一览</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-[var(--dds-gray-70)]">后端状态</span>
          {statusBadge}
        </div>
      </div>

      {/* Welcome / instruction */}
      <div className="bg-[var(--dds-blue-10)] border border-[var(--dds-blue-30)] rounded-lg p-4 text-sm text-[var(--dds-blue-80)]">
        左侧为 DDS 风格功能导航，点击任意菜单即可在右侧主区域加载对应功能页面。
      </div>

      {/* Category cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {navGroups.map((group) => (
          <div
            key={group.title}
            className="bg-[var(--color-surface)] rounded-lg border border-[var(--dds-gray-30)] shadow-[0_2px_8px_rgba(0,0,0,0.06)] hover:shadow-[0_4px_16px_rgba(0,0,0,0.1)] transition-shadow overflow-hidden flex flex-col"
          >
            <div className="px-5 py-4 border-b border-[var(--dds-gray-30)] bg-[var(--dds-gray-10)]">
              <h2 className="text-base font-semibold text-[var(--dds-slate-90)]">{group.title}</h2>
            </div>
            <div className="p-5 grid grid-cols-2 gap-2 flex-1">
              {group.items.slice(0, 6).map((item) =>
                item.href.startsWith('http') ? (
                  <a
                    key={item.href}
                    href={item.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center px-3 py-2 rounded text-sm text-[var(--dds-slate-70)] hover:bg-[var(--dds-blue-10)] hover:text-[var(--dds-blue-70)] transition-colors truncate"
                    title={item.label}
                  >
                    {item.label}
                    <span className="ml-1 text-xs opacity-60">↗</span>
                  </a>
                ) : (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="px-3 py-2 rounded text-sm text-[var(--dds-slate-70)] hover:bg-[var(--dds-blue-10)] hover:text-[var(--dds-blue-70)] transition-colors truncate"
                    title={item.label}
                  >
                    {item.label}
                  </Link>
                )
              )}
            </div>
            {group.items.length > 6 && (
              <div className="px-5 pb-4 text-xs text-[var(--dds-gray-70)]">
                还有 {group.items.length - 6} 个功能
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
