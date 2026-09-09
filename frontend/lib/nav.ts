import { translate, type Locale } from './i18n';

export interface NavItem {
  href: string;
  label: string;
  target?: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

// 导入完整的导航配置
export { getCompleteNavGroups } from './nav-complete';

// 渐进式导航展示 - 只展示核心功能，其他功能折叠到"更多功能"
export function getNavGroups(locale: Locale): NavGroup[] {
  const t = (key: string) => translate(locale, key);

  return [
    {
      title: t('nav.homeAndOverview'),
      items: [
        { href: '/', label: t('nav.home') },
        { href: '/dashboard', label: t('nav.dashboard') },
      ],
    },
    {
      title: t('nav.monitoring'),
      items: [
        { href: '/alerts', label: t('nav.alerts') },
        { href: '/anomaly', label: t('nav.anomaly') },
      ],
    },
    {
      title: t('nav.automation'),
      items: [
        { href: '/auto-heal', label: t('nav.autoHeal') },
        { href: '/chaos', label: t('nav.chaos') },
      ],
    },
    {
      title: t('nav.topology'),
      items: [
        { href: '/topology', label: t('nav.topologyFull') },
      ],
    },
    {
      title: t('nav.sre'),
      items: [
        { href: '/capacity', label: t('nav.capacity') },
        { href: '/slo', label: t('nav.slo') },
      ],
    },
    {
      title: t('nav.assets'),
      items: [
        { href: '/assets', label: t('nav.assetsManage') },
        { href: '/business-impact', label: t('nav.businessImpact') },
      ],
    },
    {
      title: t('nav.moreFeatures'),
      items: [
        { href: '/all-features', label: t('nav.viewAllFeatures') },
      ],
    },
    {
      title: t('nav.settings'),
      items: [
        { href: '/settings', label: t('nav.systemSettings') },
        { href: 'http://127.0.0.1:3000/docs', label: t('nav.apiDocs'), target: '_blank' },
      ],
    },
  ];
}

// Backward-compatible static export for consumers that do not need i18n yet.
// This will be removed once all pages are migrated to useLocale().
export const navGroups = getNavGroups('zh-CN');
