'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  Network,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  RefreshCw,
  Zap,
  Brain
} from 'lucide-react';

interface RootCauseHypothesis {
  hypothesis_id: string;
  root_cause: string;
  confidence: number;
  evidence: string[];
  causal_path: string[];
  impact_score: number;
  verification_status: string;
  verification_timestamp: string | null;
  recommended_action: string;
  requires_approval: boolean;
  expected_observations: string[];
  missing_data: string[];
}

interface HistoricalPattern {
  pattern_id: string;
  root_cause: string;
  confidence: number;
  frequency: number;
  last_occurrence: string;
  resolution_time_avg: number;
  effectiveness_score: number;
}

interface TopologyNode {
  node_id: string;
  name: string;
  layer: string;
  health_status: string;
  dependencies: string[];
  dependents: string[];
  last_updated: string;
}

interface TopologyData {
  status: string;
  topology: {
    total_nodes: number;
    layers: Record<string, number>;
    health_distribution: Record<string, number>;
  };
  nodes: Record<string, TopologyNode>;
}

export default function RootCausePage() {
  const [selectedAlert, setSelectedAlert] = useState<string>('');
  const [selectedHypothesis, setSelectedHypothesis] = useState<RootCauseHypothesis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // 获取拓扑结构
  const { data: topologyData, isLoading: topologyLoading, error: topologyError, refetch: refetchTopology } = useQuery({
    queryKey: ['root-cause-topology'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/topology');
      return resp.data as TopologyData;
    },
    refetchInterval: 60000,
  });

  // 获取历史模式
  const { data: patternsData, isLoading: patternsLoading, refetch: refetchPatterns } = useQuery({
    queryKey: ['root-cause-patterns'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/patterns?limit=20');
      return resp.data;
    },
    refetchInterval: 120000,
  });

  // 获取活跃假设
  const { data: hypothesesData, isLoading: hypothesesLoading, refetch: refetchHypotheses } = useQuery({
    queryKey: ['root-cause-hypotheses'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/hypotheses?limit=10');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  // 获取统计信息
  const { data: statisticsData, refetch: refetchStatistics } = useQuery({
    queryKey: ['root-cause-statistics'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/statistics');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const handleAnalyze = async () => {
    if (!selectedAlert) {
      return;
    }

    setIsAnalyzing(true);
    try {
      const alertData = {
        id: selectedAlert,
        title: 'Sample Alert',
        description: 'Alert for root cause analysis',
        severity: 'high',
        timestamp: new Date().toISOString(),
      };

      const metricsData = {
        cpu_usage_percent: 85,
        memory_usage_percent: 78,
        error_rate: 0.05,
        latency_ms: 250,
      };

      const resp = await api.post('/api/v1/root-cause/analyze', {
        alert: alertData,
        metrics_data: metricsData,
        context: {
          max_steps: 5,
          execution_confidence_threshold: 0.75,
          escalation_confidence_threshold: 0.60,
        },
      });

      if (resp.data?.hypotheses && resp.data.hypotheses.length > 0) {
        setSelectedHypothesis(resp.data.hypotheses[0]);
      }

      // 刷新数据
      refetchHypotheses();
      refetchTopology();
    } catch (error: any) {
      console.error('Root cause analysis failed:', error);
      if (error.response?.status === 503) {
        alert('根因智能引擎不可用，请检查后端服务配置');
      } else {
        alert('分析失败: ' + (error.response?.data?.detail || error.message));
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleVerifyHypothesis = async (hypothesisId: string) => {
    try {
      const verificationData = {
        affected_components: ['service-a', 'service-b'],
        active_components: ['service-a', 'service-b', 'database'],
        observed_symptoms: ['high_latency', 'error_spike'],
        actual_impact: {
          latency: 0.8,
          error_rate: 0.7,
        },
      };

      const resp = await api.post('/api/v1/root-cause/verify', {
        hypothesis_id: hypothesisId,
        verification_data: verificationData,
      });

      alert('验证完成: ' + resp.data.verification_result.verification_status);
      refetchHypotheses();
    } catch (error: any) {
      console.error('Verification failed:', error);
      alert('验证失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleTopologyDiscovery = async () => {
    try {
      const metricsData = {
        hosts: [
          { hostname: 'host-1', health: 'healthy', metrics: { cpu: 45, memory: 60 } },
          { hostname: 'host-2', health: 'unhealthy', metrics: { cpu: 92, memory: 88 } },
        ],
        services: [
          { name: 'api-service', health: 'healthy', port: 8080 },
          { name: 'db-service', health: 'unhealthy', port: 5432 },
        ],
      };

      const resp = await api.post('/api/v1/root-cause/topology/discover', {
        metrics_data: metricsData,
        include_dependencies: true,
      });

      alert('拓扑发现完成: 发现 ' + resp.data.discovery_result.discovered_nodes + ' 个节点');
      refetchTopology();
    } catch (error: any) {
      console.error('Topology discovery failed:', error);
      alert('拓扑发现失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const getVerificationStatusColor = (status: string) => {
    switch (status) {
      case 'verified':
        return 'bg-green-500';
      case 'partially_verified':
        return 'bg-yellow-500';
      case 'rejected':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getVerificationStatusText = (status: string) => {
    switch (status) {
      case 'verified':
        return '已验证';
      case 'partially_verified':
        return '部分验证';
      case 'rejected':
        return '已拒绝';
      default:
        return '待验证';
    }
  };

  const getHealthStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
        return 'text-green-500';
      case 'unhealthy':
        return 'text-red-500';
      case 'degraded':
        return 'text-yellow-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">根因分析</h1>
          <p className="text-sm text-gray-500 mt-1">智能根因诊断与拓扑分析</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchTopology()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新拓扑
          </Button>
          <Button onClick={handleTopologyDiscovery} variant="outline" size="sm">
            <Network className="h-4 w-4 mr-2" />
            拓扑发现
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      {statisticsData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">拓扑节点</p>
                  <p className="text-2xl font-bold">{statisticsData.statistics?.topology_nodes || 0}</p>
                </div>
                <Network className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">历史模式</p>
                  <p className="text-2xl font-bold">{statisticsData.statistics?.historical_patterns || 0}</p>
                </div>
                <Activity className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">活跃假设</p>
                  <p className="text-2xl font-bold">{statisticsData.statistics?.active_hypotheses || 0}</p>
                </div>
                <Brain className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">验证结果</p>
                  <p className="text-2xl font-bold">{statisticsData.statistics?.verification_results || 0}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="analysis" className="space-y-4">
        <TabsList>
          <TabsTrigger value="analysis">根因分析</TabsTrigger>
          <TabsTrigger value="topology">拓扑视图</TabsTrigger>
          <TabsTrigger value="patterns">历史模式</TabsTrigger>
          <TabsTrigger value="hypotheses">假设验证</TabsTrigger>
        </TabsList>

        {/* 根因分析标签页 */}
        <TabsContent value="analysis" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                智能根因分析
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="输入告警ID或描述..."
                  value={selectedAlert}
                  onChange={(e) => setSelectedAlert(e.target.value)}
                  className="flex-1"
                />
                <Button
                  onClick={handleAnalyze}
                  disabled={!selectedAlert || isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      分析中...
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-2" />
                      开始分析
                    </>
                  )}
                </Button>
              </div>

              {selectedHypothesis && (
                <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h3 className="font-semibold text-blue-900 mb-2">分析结果</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium">根因:</span> {selectedHypothesis.root_cause}
                    </div>
                    <div>
                      <span className="font-medium">置信度:</span>
                      <Badge className="ml-2">
                        {(selectedHypothesis.confidence * 100).toFixed(1)}%
                      </Badge>
                    </div>
                    <div>
                      <span className="font-medium">推荐操作:</span> {selectedHypothesis.recommended_action}
                    </div>
                    <div>
                      <span className="font-medium">因果路径:</span>
                      <div className="mt-1 text-xs text-gray-600">
                        {selectedHypothesis.causal_path.join(' → ')}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium">证据:</span>
                      <ul className="mt-1 list-disc list-inside text-xs text-gray-600">
                        {selectedHypothesis.evidence.map((evidence, idx) => (
                          <li key={idx}>{evidence}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 拓扑视图标签页 */}
        <TabsContent value="topology" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Network className="h-5 w-5" />
                系统拓扑结构
              </CardTitle>
            </CardHeader>
            <CardContent>
              {topologyLoading ? (
                <div className="text-center text-gray-500 py-8">加载拓扑数据中...</div>
              ) : topologyError ? (
                <div className="text-center text-red-500 py-8">加载失败</div>
              ) : topologyData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm text-gray-600">总节点数</div>
                      <div className="text-xl font-bold">{topologyData.topology.total_nodes}</div>
                    </div>
                    {Object.entries(topologyData.topology.layers).map(([layer, count]) => (
                      <div key={layer} className="p-3 bg-gray-50 rounded-lg">
                        <div className="text-sm text-gray-600">{layer}</div>
                        <div className="text-xl font-bold">{count}</div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4">
                    <h4 className="font-medium mb-2">节点列表</h4>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {Object.values(topologyData.nodes).map((node) => (
                        <div key={node.node_id} className="p-3 border rounded-lg">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="font-medium">{node.name}</div>
                              <div className="text-sm text-gray-600">{node.layer}</div>
                            </div>
                            <div className={`text-sm font-medium ${getHealthStatusColor(node.health_status)}`}>
                              {node.health_status}
                            </div>
                          </div>
                          <div className="mt-2 text-xs text-gray-500">
                            依赖: {node.dependencies.length} | 依赖者: {node.dependents.length}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">暂无拓扑数据</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 历史模式标签页 */}
        <TabsContent value="patterns" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                历史模式匹配
              </CardTitle>
            </CardHeader>
            <CardContent>
              {patternsLoading ? (
                <div className="text-center text-gray-500 py-8">加载历史模式中...</div>
              ) : patternsData && patternsData.patterns?.length > 0 ? (
                <div className="space-y-2">
                  {patternsData.patterns.map((pattern: HistoricalPattern) => (
                    <div key={pattern.pattern_id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium">{pattern.root_cause}</div>
                        <Badge>
                          置信度: {(pattern.confidence * 100).toFixed(1)}%
                        </Badge>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-gray-600">
                        <div>频率: {pattern.frequency}</div>
                        <div>平均解决时间: {pattern.resolution_time_avg.toFixed(1)}min</div>
                        <div>有效性: {(pattern.effectiveness_score * 100).toFixed(1)}%</div>
                        <div>最后发生: {new Date(pattern.last_occurrence).toLocaleDateString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">暂无历史模式</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 假设验证标签页 */}
        <TabsContent value="hypotheses" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                根因假设验证
              </CardTitle>
            </CardHeader>
            <CardContent>
              {hypothesesLoading ? (
                <div className="text-center text-gray-500 py-8">加载假设中...</div>
              ) : hypothesesData && hypothesesData.hypotheses?.length > 0 ? (
                <div className="space-y-4">
                  {hypothesesData.hypotheses.map((hypothesis: RootCauseHypothesis) => (
                    <div key={hypothesis.hypothesis_id} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium">{hypothesis.root_cause}</div>
                        <div className="flex items-center gap-2">
                          <Badge>
                            置信度: {(hypothesis.confidence * 100).toFixed(1)}%
                          </Badge>
                          <Badge className={getVerificationStatusColor(hypothesis.verification_status)}>
                            {getVerificationStatusText(hypothesis.verification_status)}
                          </Badge>
                        </div>
                      </div>

                      <div className="mt-2 text-sm text-gray-600">
                        <div className="mb-1">
                          <span className="font-medium">推荐操作:</span> {hypothesis.recommended_action}
                          {hypothesis.requires_approval && (
                            <Badge variant="outline" className="ml-2">需要审批</Badge>
                          )}
                        </div>

                        {hypothesis.expected_observations.length > 0 && (
                          <div className="mt-2">
                            <div className="font-medium text-xs">预期观察:</div>
                            <ul className="list-disc list-inside text-xs mt-1">
                              {hypothesis.expected_observations.map((obs, idx) => (
                                <li key={idx}>{obs}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {hypothesis.missing_data.length > 0 && (
                          <div className="mt-2">
                            <div className="font-medium text-xs">缺失数据:</div>
                            <ul className="list-disc list-inside text-xs mt-1">
                              {hypothesis.missing_data.map((data, idx) => (
                                <li key={idx}>{data}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>

                      <div className="mt-3 flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleVerifyHypothesis(hypothesis.hypothesis_id)}
                          disabled={hypothesis.verification_status === 'verified'}
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          验证假设
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">暂无活跃假设</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
