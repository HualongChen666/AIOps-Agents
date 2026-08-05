'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';

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
  'rtl',
  'ltr',
  'metric',
  'imperial',
];

export default function I18nPage() {
  const [language, setLanguage] = useState('zh-CN');
  const [timezone, setTimezone] = useState('Asia/Shanghai');
  const [unitSystem, setUnitSystem] = useState<'metric' | 'imperial'>('metric');
  const [isRTL, setIsRTL] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  const [locales, setLocales] = useState<string[]>([]);
  const [translations, setTranslations] = useState<Record<string, Record<string, string>>>({});

  // 加载支持的语言、状态以及默认语言的翻译
  useEffect(() => {
    let mounted = true;

    const loadI18nData = async () => {
      try {
        const [statusRes, localesRes] = await Promise.all([
          api.get('/api/i18n/status'),
          api.get('/api/i18n/locales'),
        ]);

        const localeList = localesRes.data?.data?.locales || [];
        const statusData = statusRes.data?.data || {};
        const defaultLocale = statusData.default_locale || localeList[0] || 'zh-CN';

        if (!mounted) return;

        setLocales(localeList);
        setLanguage(defaultLocale);

        const results = await Promise.all(
          TRANSLATION_KEYS.map((key) =>
            api.get('/api/i18n/translate', {
              params: { key, namespace: 'common', language: defaultLocale },
            })
          )
        );

        const mapped = results.reduce((acc, res, i) => {
          const key = TRANSLATION_KEYS[i];
          acc[key] = res.data?.data?.translation || key;
          return acc;
        }, {} as Record<string, string>);

        if (!mounted) return;
        setTranslations((prev) => ({ ...prev, [defaultLocale]: mapped }));
      } catch {
        // 出错时保留默认值
      }
    };

    loadI18nData();
    return () => { mounted = false; };
  }, []);

  // 语言切换时同步后端设置并懒加载对应翻译
  useEffect(() => {
    if (!language || translations[language]) return;

    let mounted = true;

    const fetchTranslations = async () => {
      try {
        const results = await Promise.all(
          TRANSLATION_KEYS.map((key) =>
            api.get('/api/i18n/translate', {
              params: { key, namespace: 'common', language },
            })
          )
        );

        const mapped = results.reduce((acc, res, i) => {
          const key = TRANSLATION_KEYS[i];
          acc[key] = res.data?.data?.translation || key;
          return acc;
        }, {} as Record<string, string>);

        if (!mounted) return;
        setTranslations((prev) => ({ ...prev, [language]: mapped }));
      } catch {
        // 失败时使用 key 作为回退
      }
    };

    fetchTranslations();

    api.post('/api/i18n/locale/set', null, { params: { locale_id: language } }).catch(() => { });

    return () => { mounted = false; };
  }, [language]);

  // 更新语言
  useEffect(() => {
    document.documentElement.lang = language;
    if (language === 'ar-SA') {
      setIsRTL(true);
    } else {
      setIsRTL(false);
    }
  }, [language]);

  // 更新RTL布局
  useEffect(() => {
    if (isRTL) {
      document.documentElement.dir = 'rtl';
      document.documentElement.classList.add('rtl');
    } else {
      document.documentElement.dir = 'ltr';
      document.documentElement.classList.remove('rtl');
    }
  }, [isRTL]);

  // 更新时间
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const t = (key: string) => {
    return translations[language]?.[key] || key;
  };

  const formatTime = (date: Date, timezone: string) => {
    return date.toLocaleString('zh-CN', {
      timeZone: timezone,
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const convertUnit = (value: number, from: 'metric' | 'imperial', to: 'metric' | 'imperial') => {
    if (from === to) return value;
    // 简单的长度转换示例：米到英尺
    if (from === 'metric' && to === 'imperial') {
      return (value * 3.28084).toFixed(2);
    }
    if (from === 'imperial' && to === 'metric') {
      return (value / 3.28084).toFixed(2);
    }
    return value;
  };

  return (
    <div className="space-y-6" dir={isRTL ? 'rtl' : 'ltr'}>
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">{t('title')}</h1>
        <div className="flex gap-2">
          <Button variant={isRTL ? 'default' : 'outline'} onClick={() => setIsRTL(true)}>
            {t('rtl')}
          </Button>
          <Button variant={!isRTL ? 'default' : 'outline'} onClick={() => setIsRTL(false)}>
            {t('ltr')}
          </Button>
        </div>
      </div>

      {/* 国际化概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">{t('language')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{language}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">{t('timezone')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{timezone}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">{t('unit')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{unitSystem === 'metric' ? t('metric') : t('imperial')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">{t('layout')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{isRTL ? 'RTL' : 'LTR'}</p>
          </CardContent>
        </Card>
      </div>

      {/* 语言设置 */}
      <Card>
        <CardHeader>
          <CardTitle>{t('language')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">选择语言</label>
            <Select value={language} onChange={(e) => setLanguage(e.target.value)}>
              {locales.map((locale) => (
                <option key={locale} value={locale}>{locale}</option>
              ))}
            </Select>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">翻译示例</h3>
            <div className="space-y-2">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="font-medium">{t('welcome')}</p>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div className="p-3 bg-blue-50 rounded-lg text-center">
                  <p className="font-medium">{t('dashboard')}</p>
                </div>
                <div className="p-3 bg-red-50 rounded-lg text-center">
                  <p className="font-medium">{t('alerts')}</p>
                </div>
                <div className="p-3 bg-green-50 rounded-lg text-center">
                  <p className="font-medium">{t('topology')}</p>
                </div>
                <div className="p-3 bg-purple-50 rounded-lg text-center">
                  <p className="font-medium">{t('settings')}</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 时区设置 */}
      <Card>
        <CardHeader>
          <CardTitle>{t('timezone')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">选择时区</label>
            <Select value={timezone} onChange={(e) => setTimezone(e.target.value)}>
              <option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</option>
              <option value="Asia/Tokyo">Asia/Tokyo (UTC+9)</option>
              <option value="America/New_York">America/New_York (UTC-5)</option>
              <option value="Europe/London">Europe/London (UTC+0)</option>
              <option value="UTC">UTC (UTC+0)</option>
            </Select>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">时区转换示例</h3>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600 mb-2">当前时间（{timezone}）:</p>
              <p className="text-2xl font-bold">{formatTime(currentTime, timezone)}</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">上海</p>
                <p className="font-medium">{formatTime(currentTime, 'Asia/Shanghai')}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">东京</p>
                <p className="font-medium">{formatTime(currentTime, 'Asia/Tokyo')}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">纽约</p>
                <p className="font-medium">{formatTime(currentTime, 'America/New_York')}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">伦敦</p>
                <p className="font-medium">{formatTime(currentTime, 'Europe/London')}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 单位转换 */}
      <Card>
        <CardHeader>
          <CardTitle>{t('unit')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">单位系统</label>
            <div className="flex gap-4">
              <Button
                variant={unitSystem === 'metric' ? 'default' : 'outline'}
                onClick={() => setUnitSystem('metric')}
              >
                {t('metric')}
              </Button>
              <Button
                variant={unitSystem === 'imperial' ? 'default' : 'outline'}
                onClick={() => setUnitSystem('imperial')}
              >
                {t('imperial')}
              </Button>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">单位转换示例</h3>
            <div className="space-y-3">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">100 米</span>
                  <span className="font-medium">
                    {convertUnit(100, 'metric', unitSystem as any)} {unitSystem === 'metric' ? '米' : '英尺'}
                  </span>
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">50 米</span>
                  <span className="font-medium">
                    {convertUnit(50, 'metric', unitSystem as any)} {unitSystem === 'metric' ? '米' : '英尺'}
                  </span>
                </div>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">1000 米</span>
                  <span className="font-medium">
                    {convertUnit(1000, 'metric', unitSystem as any)} {unitSystem === 'metric' ? '米' : '英尺'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* RTL布局演示 */}
      <Card>
        <CardHeader>
          <CardTitle>{t('layout')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-gray-600 mb-4">
              {isRTL
                ? '当前使用从右到左（RTL）布局，适用于阿拉伯语、希伯来语等语言。'
                : '当前使用从左到右（LTR）布局，适用于大多数语言。'}
            </p>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-white">
                  {isRTL ? '←' : '→'}
                </div>
                <div>
                  <p className="font-medium">导航示例</p>
                  <p className="text-sm text-gray-600">
                    {isRTL ? '从右向左阅读' : '从左向右阅读'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">布局方向切换</h3>
            <div className="flex gap-4">
              <Button variant={isRTL ? 'default' : 'outline'} onClick={() => setIsRTL(true)}>
                RTL
              </Button>
              <Button variant={!isRTL ? 'default' : 'outline'} onClick={() => setIsRTL(false)}>
                LTR
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
