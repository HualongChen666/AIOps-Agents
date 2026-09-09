/**
 * 功能实现度监控机制
 * 
 * 基于代码证据建立功能实现度矩阵，追踪：
 * - 后端API端点
 * - 前端页面
 * - 数据库表
 * - 功能状态
 */

export type FeatureStatus = 'available' | 'developing' | 'unavailable';

export interface FeatureInfo {
  status: FeatureStatus;
  api: string;
  page: string;
  table?: string;
  description?: string;
}

export const featureMatrix: Record<string, FeatureInfo> = {
  // 核心功能 - 高频使用
  'alerts': {
    status: 'available',
    api: '/api/v1/alerts',
    page: '/alerts',
    table: 'alerts',
    description: '告警管理 - 完整实现',
  },
  'dashboard': {
    status: 'available',
    api: '/api/v1/metrics/summary',
    page: '/dashboard',
    table: 'metrics',
    description: '仪表盘 - 完整实现',
  },
  'topology': {
    status: 'available',
    api: '/api/v1/topologies/full-link',
    page: '/topology',
    table: 'topologies',
    description: '全链路拓扑 - 完整实现',
  },
  'auto-heal': {
    status: 'available',
    api: '/api/v1/repairs',
    page: '/auto-heal',
    table: 'repairs',
    description: '自动修复 - 完整实现',
  },

  // 核心功能 - 中频使用
  'capacity': {
    status: 'available',
    api: '/api/v1/capacity/forecast',
    page: '/capacity',
    table: 'capacity_forecasts',
    description: '容量管理 - 完整实现',
  },
  'anomaly': {
    status: 'available',
    api: '/api/v1/anomaly/records',
    page: '/anomaly',
    table: 'anomaly_records',
    description: '异常检测 - 完整实现',
  },
  'assets': {
    status: 'available',
    api: '/api/v1/assets',
    page: '/assets',
    table: 'assets',
    description: '资产管理 - 完整实现',
  },
  'business-impact': {
    status: 'available',
    api: '/api/v1/business-impact',
    page: '/business-impact',
    table: 'business_impact',
    description: '业务影响 - 完整实现',
  },

  // AI功能 - 完整实现但非核心需求
  'ai-llm-router': {
    status: 'available',
    api: '/api/ai/llm-router',
    page: '/ai/llm-router',
    table: 'llm_models',
    description: 'LLM路由器 - 完整实现',
  },
  'ai-rag-knowledge-base': {
    status: 'available',
    api: '/api/ai/knowledge-base',
    page: '/ai/rag-knowledge-base',
    table: 'knowledge_bases',
    description: 'RAG知识库 - 完整实现',
  },
  'ai-vectorizer': {
    status: 'available',
    api: '/api/ai/vectorizer',
    page: '/ai/vectorizer',
    table: 'vectorizer_configs',
    description: '向量化处理 - 完整实现',
  },
  'ai-knowledge-graph': {
    status: 'available',
    api: '/api/ai/knowledge-graph',
    page: '/ai/knowledge-graph',
    table: 'knowledge_graph',
    description: '知识图谱 - 完整实现',
  },
  'ai-cost-optimizer': {
    status: 'available',
    api: '/api/ai/cost-optimizer',
    page: '/ai/cost-optimizer',
    table: 'cost_optimizations',
    description: '成本优化器 - 完整实现',
  },
  'ai-capability-evaluator': {
    status: 'available',
    api: '/api/ai/capability-evaluator',
    page: '/ai/capability-evaluator',
    table: 'model_capabilities',
    description: '能力评估器 - 完整实现',
  },
  'ai-load-balancer': {
    status: 'available',
    api: '/api/ai/load-balancer',
    page: '/ai/load-balancer',
    table: 'load_balancers',
    description: '负载均衡器 - 完整实现',
  },
};

/**
 * 获取功能状态
 */
export function getFeatureStatus(featureKey: string): FeatureStatus {
  return featureMatrix[featureKey]?.status || 'unavailable';
}

/**
 * 检查功能是否可用
 */
export function isFeatureAvailable(featureKey: string): boolean {
  return getFeatureStatus(featureKey) === 'available';
}

/**
 * 获取所有可用功能
 */
export function getAvailableFeatures(): string[] {
  return Object.entries(featureMatrix)
    .filter(([_, info]) => info.status === 'available')
    .map(([key, _]) => key);
}

/**
 * 获取功能统计
 */
export function getFeatureStats() {
  const stats = {
    total: Object.keys(featureMatrix).length,
    available: 0,
    developing: 0,
    unavailable: 0,
  };

  Object.values(featureMatrix).forEach((info) => {
    stats[info.status]++;
  });

  return stats;
}
