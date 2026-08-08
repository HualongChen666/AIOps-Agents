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

export function getNavGroups(locale: Locale): NavGroup[] {
  const t = (key: string) => translate(locale, key);

  return [
    {
      title: t('nav.overview'),
      items: [
        { href: '/', label: t('nav.overview') },
        { href: '/overview', label: t('nav.overview') },
        { href: '/dashboard', label: t('nav.dashboard') },
        { href: '/kpi', label: t('nav.kpi') },
      ],
    },
    {
      title: t('nav.monitoring'),
      items: [
        { href: '/alerts', label: t('nav.alerts') },
        { href: '/anomaly', label: t('nav.anomaly') },
        { href: '/security', label: t('nav.security') },
        { href: '/security-events', label: t('nav.securityEvents') },
        { href: '/approval', label: t('nav.approval') },
      ],
    },
    {
      title: t('nav.observability'),
      items: [
        { href: '/metrics', label: t('nav.metrics') },
        { href: '/metrics-explorer', label: t('nav.metricsExplorer') },
        { href: '/log-analysis', label: t('nav.logAnalysis') },
        { href: '/query', label: t('nav.query') },
        { href: '/query-editor', label: t('nav.queryEditor') },
      ],
    },
    {
      title: t('nav.sre'),
      items: [
        { href: '/slo', label: t('nav.slo') },
        { href: '/capacity', label: t('nav.capacity') },
        { href: '/performance', label: t('nav.performance') },
        { href: '/predictive', label: t('nav.predictive') },
      ],
    },
    {
      title: t('nav.topology'),
      items: [
        { href: '/topology', label: t('nav.topologyFull') },
        { href: '/topology-enhanced', label: t('nav.topologyEnhanced') },
        { href: '/service-map', label: t('nav.serviceMap') },
      ],
    },
    {
      title: t('nav.automation'),
      items: [
        { href: '/auto-heal', label: t('nav.autoHeal') },
        { href: '/workflow', label: t('nav.workflow') },
        { href: '/root-cause', label: t('nav.rootCause') },
        { href: '/change-management', label: t('nav.changeManagement') },
        { href: '/chaos', label: t('nav.chaos') },
        { href: '/chaos-engineering', label: t('nav.chaosConsole') },
      ],
    },
    {
      title: t('nav.aiAssistant'),
      items: [{ href: '/ai-copilot', label: t('nav.aiCopilot') }],
    },
    {
      title: t('nav.assets'),
      items: [
        { href: '/assets', label: t('nav.assetsManage') },
        { href: '/business-impact', label: t('nav.businessImpact') },
        { href: '/cost', label: t('nav.cost') },
        { href: '/maturity', label: t('nav.maturity') },
        { href: '/audit', label: t('nav.audit') },
        { href: '/compliance-audit', label: t('nav.complianceAudit') },
      ],
    },
    {
      title: t('nav.users'),
      items: [
        { href: '/users', label: t('nav.userManage') },
        { href: '/knowledge', label: t('nav.knowledge') },
        { href: '/knowledge-base', label: t('nav.knowledgeBase') },
        { href: '/history', label: t('nav.ragHistory') },
        { href: '/collaboration', label: t('nav.collaboration') },
        { href: '/team-collaboration', label: t('nav.teamCollaboration') },
        { href: '/tenant', label: t('nav.tenant') },
        { href: '/multi-tenant', label: t('nav.multiTenant') },
      ],
    },
    {
      title: t('nav.settings'),
      items: [
        { href: '/settings', label: t('nav.systemSettings') },
        { href: '/i18n', label: t('nav.i18n') },
        { href: 'http://127.0.0.1:3000/docs', label: t('nav.apiDocs'), target: '_blank' },
      ],
    },
  ];
}

// Backward-compatible static export for consumers that do not need i18n yet.
// This will be removed once all pages are migrated to useLocale().
export const navGroups = getNavGroups('zh-CN');
