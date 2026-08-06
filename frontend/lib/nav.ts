export interface NavItem {
  href: string;
  label: string;
  target?: string;
}

export interface NavGroup {
  title: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    title: '总览与核心',
    items: [
      { href: '/', label: '功能门户' },
      { href: '/overview', label: '总览' },
      { href: '/dashboard', label: '仪表盘' },
      { href: '/kpi', label: 'KPI' },
      { href: '/metrics', label: '指标' },
      { href: '/metrics-explorer', label: '指标探索' },
    ],
  },
  {
    title: '告警与事件',
    items: [
      { href: '/alerts', label: '告警中心' },
      { href: '/anomaly', label: '异常检测' },
      { href: '/security', label: '安全中心' },
      { href: '/security-events', label: '安全事件' },
      { href: '/approval', label: 'HITL 审批' },
    ],
  },
  {
    title: '拓扑与依赖',
    items: [
      { href: '/topology', label: '全链路拓扑' },
      { href: '/topology-enhanced', label: '增强拓扑' },
      { href: '/service-map', label: '服务地图' },
    ],
  },
  {
    title: '容量、性能与稳定性',
    items: [
      { href: '/capacity', label: '容量预测' },
      { href: '/performance', label: '性能分析' },
      { href: '/slo', label: 'SLO' },
      { href: '/slo-sla', label: 'SLO/SLA' },
      { href: '/predictive', label: '预测分析' },
    ],
  },
  {
    title: '自动化、根因与变更',
    items: [
      { href: '/auto-heal', label: '自动自愈' },
      { href: '/workflow', label: '工作流' },
      { href: '/workflow-orchestration', label: '工作流编排' },
      { href: '/root-cause', label: '根因分析' },
      { href: '/change-management', label: '变更管理' },
      { href: '/chaos', label: '混沌工程' },
      { href: '/chaos-engineering', label: '混沌控制台' },
    ],
  },
  {
    title: '可观测性',
    items: [
      { href: '/log-analysis', label: '日志分析' },
      { href: '/query', label: '查询' },
      { href: '/query-editor', label: '查询编辑器' },
    ],
  },
  {
    title: '审计、治理与评估',
    items: [
      { href: '/audit', label: '审计中心' },
      { href: '/compliance-audit', label: '合规审计' },
      { href: '/business-impact', label: '业务影响' },
      { href: '/cost', label: '成本分析' },
      { href: '/maturity', label: '成熟度评估' },
    ],
  },
  {
    title: '知识、协作与租户',
    items: [
      { href: '/knowledge', label: '知识' },
      { href: '/knowledge-base', label: '知识库' },
      { href: '/history', label: 'RAG 历史' },
      { href: '/collaboration', label: '协作' },
      { href: '/team-collaboration', label: '团队协作' },
      { href: '/tenant', label: '租户' },
      { href: '/multi-tenant', label: '多租户' },
      { href: '/i18n', label: '国际化' },
    ],
  },
  {
    title: 'AI 助手',
    items: [
      { href: '/ai-copilot', label: 'AI Copilot' },
    ],
  },
  {
    title: '组件与示例',
    items: [
      { href: '/advanced-table', label: '高级表格' },
      { href: '/animation', label: '动画' },
      { href: '/builder', label: '构建器' },
      { href: '/charts', label: '图表' },
      { href: '/forms', label: '表单' },
      { href: '/mobile', label: '移动端' },
      { href: '/feedback', label: '反馈' },
    ],
  },
  {
    title: '后端与系统',
    items: [
      { href: '/settings', label: '系统设置' },
      { href: 'http://127.0.0.1:3000/docs', label: 'API 文档', target: '_blank' },
    ],
  },
];
