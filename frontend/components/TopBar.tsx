'use client';

import { useMemo } from 'react';
import { useI18n, useLocale, type Locale } from '@/lib/i18n';

export function TopBar() {
  const { locale, setLocale } = useLocale();
  const t = useI18n();

  const locales: { key: Locale; label: string }[] = useMemo(
    () => [
      { key: 'zh-CN', label: t('lang.zh-CN') },
      { key: 'en-US', label: t('lang.en-US') },
    ],
    [t]
  );

  return (
    <header className="h-14 shrink-0 flex items-center justify-between px-6 bg-[var(--dds-slate-90)] border-b border-[var(--dds-slate-70)]">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-md bg-[var(--dds-blue-60)] flex items-center justify-center text-white font-bold text-sm">
          A
        </div>
        <span className="text-white font-semibold text-sm">{t('app.name')}</span>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-xs text-[var(--dds-slate-30)]" aria-hidden>
          {t('topbar.language')}
        </span>
        <div className="flex rounded-md overflow-hidden border border-[var(--dds-slate-60)]">
          {locales.map(({ key, label }) => {
            const active = locale === key;
            return (
              <button
                key={key}
                onClick={() => setLocale(key)}
                className={`px-3 py-1 text-xs font-medium transition-colors ${
                  active
                    ? 'bg-[var(--dds-blue-60)] text-white'
                    : 'bg-[var(--dds-slate-80)] text-[var(--dds-slate-30)] hover:bg-[var(--dds-slate-70)] hover:text-white'
                }`}
                aria-pressed={active}
                type="button"
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
