'use client'

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';

interface LocaleInfo {
  locale_id: string;
  language?: string;
  region?: string;
  timezone?: string;
  currency?: string;
}

const TRANSLATION_KEYS = [
  'title',
  'language',
  'timezone',
  'unit',
  'layout',
  'welcome',
  'dashboard',
  'alerts',
  'topology',
  'settings',
  'metric',
  'imperial',
];

export default function I18nPage() {
  const [locales, setLocales] = useState<LocaleInfo[]>([]);
  const [selectedLocale, setSelectedLocale] = useState<string>('');
  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const loadInitial = async () => {
      try {
        const localesRes = await api.get('/api/i18n/locales');

        const list = localesRes.data?.data?.locales || [];
        const defaultLocale = list[0]?.locale_id || 'zh-CN';

        if (!mounted) return;
        setLocales(list);
        setSelectedLocale(defaultLocale);
      } catch {
        setLocales([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadInitial();
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (!selectedLocale) return;

    let mounted = true;

    const loadTranslations = async () => {
      setLoading(true);
      try {
        await api.post('/api/i18n/locale/set', null, {
          params: { locale_id: selectedLocale },
        });

        const results = await Promise.all(
          TRANSLATION_KEYS.map((key) =>
            api.get('/api/i18n/translate', {
              params: { key, namespace: 'common' },
            })
          )
        );

        const mapped: Record<string, string> = {};
        results.forEach((res, i) => {
          mapped[TRANSLATION_KEYS[i]] = res.data?.data?.translation ?? TRANSLATION_KEYS[i];
        });

        if (mounted) setTranslations(mapped);
      } catch {
        if (mounted) setTranslations({});
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadTranslations();
    return () => { mounted = false; };
  }, [selectedLocale]);

  const handleSave = async (key: string, value: string) => {
    setSavingKey(key);
    try {
      await api.put('/api/i18n/translate', null, {
        params: {
          key,
          namespace: 'common',
          language: selectedLocale,
          translation: value,
        },
      });
      setTranslations((prev) => ({ ...prev, [key]: value }));
    } catch {
      // api interceptor shows errors
    } finally {
      setSavingKey(null);
    }
  };

  if (loading && !locales.length) {
    return <div className="text-center text-gray-500 py-10">加载中...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">国际化管理</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">当前语言</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{selectedLocale || '-'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">支持语言数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{locales.length}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>语言设置</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">选择语言</label>
            <Select
              value={selectedLocale}
              onChange={(e) => setSelectedLocale(e.target.value)}
            >
              {locales.map((locale) => (
                <option key={locale.locale_id} value={locale.locale_id}>
                  {locale.locale_id} {locale.region ? `(${locale.region})` : ''}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">翻译编辑</h3>
            {loading ? (
              <p className="text-sm text-gray-500">加载翻译中...</p>
            ) : (
              <div className="space-y-3">
                {TRANSLATION_KEYS.map((key) => (
                  <div key={key} className="flex items-center gap-3">
                    <div className="w-32 shrink-0 text-sm font-medium text-gray-700 truncate">
                      {key}
                    </div>
                    <Input
                      value={translations[key] ?? key}
                      onChange={(e) =>
                        setTranslations((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      className="flex-1"
                    />
                    <Button
                      size="sm"
                      disabled={savingKey === key}
                      onClick={() => handleSave(key, translations[key] ?? key)}
                    >
                      {savingKey === key ? '保存中' : '保存'}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
