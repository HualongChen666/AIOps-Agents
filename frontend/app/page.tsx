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
      <span className="text-yellow-500">● 检测中</span>
    ) : status === 'ok' ? (
      <span className="text-green-500">● 后端正常</span>
    ) : (
      <span className="text-red-500">● 后端不可用</span>
    );

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">AIOps Agent 统一控制台</h1>
          <p className="text-gray-500 mt-1">企业级 AI 运维监控平台 · 功能总览</p>
        </div>
        <div className="text-sm font-medium">{statusBadge}</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {navGroups.map((group) => (
          <div
            key={group.title}
            className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm"
          >
            <h2 className="text-lg font-semibold mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
              {group.title}
            </h2>
            <div className="grid grid-cols-2 gap-2">
              {group.items.slice(0, 6).map((item) =>
                item.href.startsWith('http') ? (
                  <a
                    key={item.href}
                    href={item.href}
                    target="_blank"
                    className="px-3 py-2 rounded-md text-sm bg-gray-100 dark:bg-gray-700 hover:bg-blue-100 dark:hover:bg-blue-900 transition truncate"
                    title={item.label}
                  >
                    {item.label} ↗
                  </a>
                ) : (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="px-3 py-2 rounded-md text-sm bg-gray-100 dark:bg-gray-700 hover:bg-blue-100 dark:hover:bg-blue-900 transition truncate"
                    title={item.label}
                  >
                    {item.label}
                  </Link>
                )
              )}
            </div>
            {group.items.length > 6 && (
              <p className="text-xs text-gray-500 mt-3">还有 {group.items.length - 6} 个功能</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
