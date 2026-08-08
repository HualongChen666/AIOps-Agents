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
    api
      .get('/api/v1/health/ping')
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'));
  }, []);

  const statusBadge =
    status === 'loading' ? (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-[var(--dds-yellow-10)] text-[var(--dds-yellow-70)]">
        <span className="w-2 h-2 rounded-full bg-[var(--dds-yellow-60)] mr-2 animate-pulse" />
        {t('home.status.loading')}
      </span>
    ) : status === 'ok' ? (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-[var(--dds-green-10)] text-[var(--dds-green-70)]">
        <span className="w-2 h-2 rounded-full bg-[var(--dds-green-60)] mr-2" />
        {t('home.status.ok')}
      </span>
    ) : (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-[var(--dds-red-10)] text-[var(--dds-red-70)]">
        <span className="w-2 h-2 rounded-full bg-[var(--dds-red-60)] mr-2" />
        {t('home.status.error')}
      </span>
    );

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-[var(--dds-gray-30)]">
        <div>
          <h1 className="text-3xl font-bold text-[var(--dds-slate-90)] mb-1">{t('home.title')}</h1>
          <p className="text-[var(--dds-gray-70)] text-sm">{t('home.subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-[var(--dds-gray-70)]">{t('home.backendStatus')}</span>
          {statusBadge}
        </div>
      </div>

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
                +{group.items.length - 6}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
