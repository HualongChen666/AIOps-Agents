'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

type ReactNode = import('react').ReactNode;

export type Locale = 'zh-CN' | 'en-US';
export const DEFAULT_LOCALE: Locale = 'zh-CN';
export const SUPPORTED_LOCALES: Locale[] = ['zh-CN', 'en-US'];

type Dictionary = Record<string, string>;

const zhCN: Dictionary = {
  'app.name': 'AIOps Agent',
  'app.subtitle': '统一运维控制台',
  'home.title': 'AIOps Agent 统一控制台',
  'home.subtitle': '企业级 AI 运维监控平台 · 全部功能一览',
  'home.backendStatus': '后端状态',
  'home.status.loading': '检测中',
  'home.status.ok': '后端正常',
  'home.status.error': '后端不可用',
  'topbar.language': '语言',
  'lang.zh-CN': '中',
  'lang.en-US': 'EN',
  'nav.overview': '总览',
  'nav.dashboard': '仪表盘',
  'nav.kpi': 'KPI',
  'nav.monitoring': '监控告警',
  'nav.alerts': '告警中心',
  'nav.anomaly': '异常检测',
  'nav.security': '安全中心',
  'nav.securityEvents': '安全事件',
  'nav.approval': 'HITL 审批',
  'nav.observability': '可观测性',
  'nav.metrics': '指标',
  'nav.metricsExplorer': '指标探索',
  'nav.logAnalysis': '日志分析',
  'nav.query': '查询',
  'nav.queryEditor': '查询编辑器',
  'nav.sre': 'SRE 稳定性',
  'nav.slo': 'SLO/SLA',
  'nav.capacity': '容量预测',
  'nav.performance': '性能分析',
  'nav.predictive': '预测分析',
  'nav.topology': '拓扑依赖',
  'nav.topologyFull': '全链路拓扑',
  'nav.topologyEnhanced': '增强拓扑',
  'nav.serviceMap': '服务地图',
  'nav.automation': '自动化运维',
  'nav.autoHeal': '自动自愈',
  'nav.workflow': '工作流',
  'nav.rootCause': '根因分析',
  'nav.changeManagement': '变更管理',
  'nav.chaos': '混沌工程',
  'nav.chaosConsole': '混沌控制台',
  'nav.aiAssistant': 'AI 助手',
  'nav.aiCopilot': 'AI Copilot',
  'nav.assets': '资产治理',
  'nav.assetsManage': '资产管理',
  'nav.businessImpact': '业务影响',
  'nav.cost': '成本分析',
  'nav.maturity': '成熟度评估',
  'nav.audit': '审计中心',
  'nav.complianceAudit': '合规审计',
  'nav.users': '用户与协作',
  'nav.userManage': '用户管理',
  'nav.knowledge': '知识',
  'nav.knowledgeBase': '知识库',
  'nav.ragHistory': 'RAG 历史',
  'nav.collaboration': '协作',
  'nav.teamCollaboration': '团队协作',
  'nav.tenant': '租户',
  'nav.multiTenant': '多租户',
  'nav.settings': '系统设置',
  'nav.systemSettings': '系统设置',
  'nav.i18n': '国际化',
  'nav.apiDocs': 'API 文档',
  'sidenav.logout': '退出登录',
  'sidenav.collapse': '收起侧边栏',
  'sidenav.expand': '展开侧边栏',
};

const enUS: Dictionary = {
  ...zhCN,
  'app.name': 'AIOps Agent',
  'app.subtitle': 'Unified Ops Console',
  'home.title': 'AIOps Agent Unified Console',
  'home.subtitle': 'Enterprise AI Ops Monitoring Platform · All Features',
  'home.backendStatus': 'Backend Status',
  'home.status.loading': 'Checking',
  'home.status.ok': 'Backend Online',
  'home.status.error': 'Backend Offline',
  'topbar.language': 'Language',
  'nav.overview': 'Overview',
  'nav.dashboard': 'Dashboard',
  'nav.kpi': 'KPI',
  'nav.monitoring': 'Monitoring & Alerts',
  'nav.alerts': 'Alert Center',
  'nav.anomaly': 'Anomaly Detection',
  'nav.security': 'Security',
  'nav.securityEvents': 'Security Events',
  'nav.approval': 'HITL Approval',
  'nav.observability': 'Observability',
  'nav.metrics': 'Metrics',
  'nav.metricsExplorer': 'Metrics Explorer',
  'nav.logAnalysis': 'Log Analysis',
  'nav.query': 'Query',
  'nav.queryEditor': 'Query Editor',
  'nav.sre': 'SRE Stability',
  'nav.slo': 'SLO/SLA',
  'nav.capacity': 'Capacity',
  'nav.performance': 'Performance',
  'nav.predictive': 'Predictive',
  'nav.topology': 'Topology',
  'nav.topologyFull': 'Full Topology',
  'nav.topologyEnhanced': 'Enhanced Topology',
  'nav.serviceMap': 'Service Map',
  'nav.automation': 'Automation',
  'nav.autoHeal': 'Auto Heal',
  'nav.workflow': 'Workflow',
  'nav.rootCause': 'Root Cause',
  'nav.changeManagement': 'Change Mgmt',
  'nav.chaos': 'Chaos Eng',
  'nav.chaosConsole': 'Chaos Console',
  'nav.aiAssistant': 'AI Assistant',
  'nav.aiCopilot': 'AI Copilot',
  'nav.assets': 'Asset Governance',
  'nav.assetsManage': 'Asset Management',
  'nav.businessImpact': 'Business Impact',
  'nav.cost': 'Cost Analysis',
  'nav.maturity': 'Maturity',
  'nav.audit': 'Audit',
  'nav.complianceAudit': 'Compliance Audit',
  'nav.users': 'Users & Collab',
  'nav.userManage': 'User Management',
  'nav.knowledge': 'Knowledge',
  'nav.knowledgeBase': 'Knowledge Base',
  'nav.ragHistory': 'RAG History',
  'nav.collaboration': 'Collaboration',
  'nav.teamCollaboration': 'Team Collab',
  'nav.tenant': 'Tenant',
  'nav.multiTenant': 'Multi Tenant',
  'nav.settings': 'Settings',
  'nav.systemSettings': 'System Settings',
  'nav.i18n': 'I18n',
  'nav.apiDocs': 'API Docs',
  'sidenav.logout': 'Logout',
  'sidenav.collapse': 'Collapse',
  'sidenav.expand': 'Expand',
};

const dictionaries: Record<Locale, Dictionary> = {
  'zh-CN': zhCN,
  'en-US': enUS,
};

function setCookie(name: string, value: string, days = 365) {
  if (typeof document === 'undefined') return;
  const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function translate(locale: Locale, key: string): string {
  return dictionaries[locale]?.[key] ?? key;
}

interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: DEFAULT_LOCALE,
  setLocale: () => {},
  t: (key) => key,
});

export function useLocale() {
  return useContext(LocaleContext);
}

export function useI18n() {
  const { t } = useContext(LocaleContext);
  return t;
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  useEffect(() => {
    const stored = (typeof window !== 'undefined' && localStorage.getItem('locale')) || getCookie('locale');
    if (stored && SUPPORTED_LOCALES.includes(stored as Locale)) {
      setLocaleState(stored as Locale);
    }
  }, []);

  const setLocale = useCallback((next: Locale) => {
    if (!SUPPORTED_LOCALES.includes(next)) return;
    setLocaleState(next);
    if (typeof window !== 'undefined') {
      localStorage.setItem('locale', next);
    }
    setCookie('locale', next);
    if (typeof document !== 'undefined') {
      document.documentElement.lang = next;
    }
  }, []);

  const t = useCallback((key: string) => translate(locale, key), [locale]);

  const value = useMemo<LocaleContextValue>(() => ({ locale, setLocale, t }), [locale, setLocale, t]);

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = locale;
    }
  }, [locale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}
