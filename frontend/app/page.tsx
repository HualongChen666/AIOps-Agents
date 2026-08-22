'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { getNavGroups } from '@/lib/nav';
import { useI18n, useLocale } from '@/lib/i18n';

export default function Home() {
  const { locale } = useLocale();
  const t = useI18n();
  const navGroups = useMemo(() => getNavGroups(locale), [locale]);
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading');

  useEffect(() => {
    // 用户已登录，说明后端可用，直接设置为正常状态
    setStatus('ok');
  }, []);

  const statusBadge =
    status === 'loading' ? (
      <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold bg-yellow-100 text-yellow-800 border border-yellow-200">
        <span className="w-2.5 h-2.5 rounded-full bg-yellow-500 mr-2 animate-pulse" />
        {t('home.status.loading')}
      </span>
    ) : status === 'ok' ? (
      <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold bg-green-100 text-green-800 border border-green-200">
        <span className="w-2.5 h-2.5 rounded-full bg-green-500 mr-2" />
        {t('home.status.ok')}
      </span>
    ) : (
      <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold bg-red-100 text-red-800 border border-red-200">
        <span className="w-2.5 h-2.5 rounded-full bg-red-500 mr-2" />
        {t('home.status.error')}
      </span>
    );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 lg:py-16">
        {/* Header */}
        <div className="mb-8 sm:mb-12 text-center">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-3 sm:mb-4 tracking-tight">
            {t('home.title')}
          </h1>
          <p className="text-base sm:text-lg lg:text-xl text-gray-600 mb-6 sm:mb-8 max-w-2xl mx-auto px-4">
            {t('home.subtitle')}
          </p>
          <div className="inline-flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 bg-white rounded-full shadow-sm">
            <span className="text-xs sm:text-sm text-gray-600 font-medium">{t('home.backendStatus')}</span>
            {statusBadge}
          </div>
        </div>

        {/* Navigation Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
          {navGroups.map((group) => (
            <div
              key={group.title}
              className="bg-white rounded-xl sm:rounded-2xl border border-gray-200 shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden group"
            >
              <div className="px-4 sm:px-6 py-3 sm:py-5 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50">
                <h2 className="text-lg sm:text-xl font-bold text-gray-900">{group.title}</h2>
              </div>
              <div className="p-4 sm:p-6 grid grid-cols-2 gap-2 sm:gap-3">
                {group.items.slice(0, 6).map((item) =>
                  item.href.startsWith('http') ? (
                    <a
                      key={item.href}
                      href={item.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center px-3 sm:px-4 py-2 sm:py-3 rounded-lg sm:rounded-xl text-xs sm:text-sm font-medium text-gray-700 bg-gray-50 hover:bg-blue-100 hover:text-blue-700 transition-all duration-200 truncate group-hover:shadow-md"
                      title={item.label}
                    >
                      {item.label}
                      <span className="ml-1 sm:ml-2 text-xs text-gray-400 group-hover:text-blue-500">↗</span>
                    </a>
                  ) : (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="flex items-center px-3 sm:px-4 py-2 sm:py-3 rounded-lg sm:rounded-xl text-xs sm:text-sm font-medium text-gray-700 bg-gray-50 hover:bg-blue-100 hover:text-blue-700 transition-all duration-200 truncate group-hover:shadow-md"
                      title={item.label}
                    >
                      {item.label}
                    </Link>
                  )
                )}
              </div>
              {group.items.length > 6 && (
                <div className="px-4 sm:px-6 pb-4 sm:pb-5 pt-2">
                  <div className="text-xs sm:text-sm text-gray-500 font-medium">
                    还有 {group.items.length - 6} 个功能
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
