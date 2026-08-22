'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { KpiCard } from '@/components/ui/KpiCard';
import { Network, RefreshCw, Search, TrendingUp, CheckCircle, AlertTriangle, Plus, Trash2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface TopologyNode {
  node_id: string;
  name: string;
  layer: string;
  health_status: string;
  dependencies: string[];
  dependents: string[];
  last_updated: string;
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

interface RootCauseHypothesis {
  hypothesis_id: string;
  root_cause: string;
  confidence: number;
  evidence: Record<string, any>;
  causal_path: string[];
  impact_score: number;
  verification_status: string;
  verification_timestamp: string | null;
}

interface RootCauseStatistics {
  total_analyses: number;
  successful_analyses: number;
  average_confidence: number;
  top_root_causes: Array<{ root_cause: string; count: number }>;
}

export default function RootCauseAnalysisPage() {
  const [activeTab, setActiveTab] = useState<'topology' | 'patterns' | 'hypotheses' | 'analysis'>('topology');
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [showPatternModal, setShowPatternModal] = useState(false);
  const [analysisData, setAnalysisData] = useState({
    alert: { id: '' },
    metrics_data: {},
    context: {},
  });
  const [patternData, setPatternData] = useState({
    symptoms: {},
    root_cause: '',
    resolution_time: 0,
    effectiveness: 0,
  });

  const queryClient = useQueryClient();

  // 🔧 获取拓扑结构
  const { data: topologyData, isLoading: topologyLoading, refetch: refetchTopology } = useQuery<{ topology: Record<string, any>; nodes: Record<string, TopologyNode> }>({
    queryKey: ['root-cause-topology'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/topology');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 获取历史模式
  const { data: patternsData, isLoading: patternsLoading, refetch: refetchPatterns } = useQuery<{ patterns: HistoricalPattern[]; total_patterns: number }>({
    queryKey: ['root-cause-patterns'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/patterns?limit=50');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取活跃假设
  const { data: hypothesesData, isLoading: hypothesesLoading, refetch: refetchHypotheses } = useQuery<{ hypotheses: RootCauseHypothesis[]; total_hypotheses: number }>({
    queryKey: ['root-cause-hypotheses'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/hypotheses?limit=20');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 获取统计信息
  const { data: statisticsData, isLoading: statisticsLoading, refetch: refetchStatistics } = useQuery<{ statistics: RootCauseStatistics }>({
    queryKey: ['root-cause-statistics'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/statistics');
      return resp.data;
    },
    refetchInterval: 300000, // 5分钟刷新
  });

  // 🔧 根因分析
  const analyzeRootCauseMutation = useMutation({
    mutationFn: async (data: typeof analysisData) => {
      const resp = await api.post('/api/v1/root-cause/analyze', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['root-cause-hypotheses'] });
      setShowAnalysisModal(false);
      showSuccess('根因分析成功');
    },
    onError: () => {
      showError('根因分析失败');
    },
  });

  // 🔧 学习历史模式
  const learnPatternMutation = useMutation({
    mutationFn: async (data: typeof patternData) => {
      const resp = await api.post('/api/v1/root-cause/patterns/learn', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['root-cause-patterns'] });
      setShowPatternModal(false);
      showSuccess('历史模式已学习');
    },
    onError: () => {
      showError('学习模式失败');
    },
  });

  // 🔧 删除假设
  const deleteHypothesisMutation = useMutation({
    mutationFn: async (hypothesisId: string) => {
      const resp = await api.delete(`/api/v1/root-cause/hypotheses/${hypothesisId}`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['root-cause-hypotheses'] });
      showSuccess('假设已删除');
    },
    onError: () => {
      showError('删除假设失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(
    topologyLoading || patternsLoading || hypothesesLoading || statisticsLoading
  );

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (pageError) {
      showError('Failed to load root cause data');
      setPageError(pageError as Error);
    }
  }, [pageError, showError, setPageError]);

  const topology = topologyData || { topology: {}, nodes: {} };
  const patterns = patternsData || { patterns: [], total_patterns: 0 };
  const hypotheses = hypothesesData || { hypotheses: [], total_hypotheses: 0 };
  const statistics = statisticsData || { statistics: { total_analyses: 0, successful_analyses: 0, average_confidence: 0, top_root_causes: [] } };

  const handleRootCauseAnalysis = () => {
    analyzeRootCauseMutation.mutate(analysisData);
  };

  const handlePatternLearning = () => {
    learnPatternMutation.mutate(patternData);
  };

  const handleDeleteHypothesis = (hypothesisId: string) => {
    deleteHypothesisMutation.mutate(hypothesisId);
  };

  const handleRefresh = () => {
    refetchTopology();
    refetchPatterns();
    refetchHypotheses();
    refetchStatistics();
  };

  // 🔧 P1 Integration: Use enhanced loading and empty states
  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载根因分析数据，请稍后重试"
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Network className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">根因分析</h1>
            <p className="text-sm text-gray-500">智能根因分析和故障诊断</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总分析次数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{statistics.statistics.total_analyses}</p>
            <p className="text-sm text-gray-500 mt-1">根因分析总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">成功率</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {statistics.statistics.total_analyses > 0
                ? ((statistics.statistics.successful_analyses / statistics.statistics.total_analyses) * 100).toFixed(1)
                : 0}%
            </p>
            <p className="text-sm text-gray-500 mt-1">分析成功率</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均置信度</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-purple-600">
              {(statistics.statistics.average_confidence * 100).toFixed(1)}%
            </p>
            <p className="text-sm text-gray-500 mt-1">假设平均置信度</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃假设</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-orange-600">{hypotheses.total_hypotheses}</p>
            <p className="text-sm text-gray-500 mt-1">当前活跃假设数</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'topology' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('topology')}
        >
          <Network className="h-4 w-4 mr-2" />
          拓扑结构
        </Button>
        <Button
          variant={activeTab === 'patterns' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('patterns')}
        >
          <Search className="h-4 w-4 mr-2" />
          历史模式
        </Button>
        <Button
          variant={activeTab === 'hypotheses' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('hypotheses')}
        >
          <TrendingUp className="h-4 w-4 mr-2" />
          活跃假设
        </Button>
        <Button
          variant={activeTab === 'analysis' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('analysis')}
        >
          <CheckCircle className="h-4 w-4 mr-2" />
          根因分析
        </Button>
      </div>

      {/* Topology Tab */}
      {activeTab === 'topology' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              系统拓扑结构
            </CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(topology.nodes).length > 0 ? (
              <div className="space-y-4">
                {Object.entries(topology.nodes).map(([nodeId, node]) => (
                  <div key={nodeId} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${node.health_status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
                        <span className="font-semibold">{node.name}</span>
                        <StatusBadge status={node.health_status as "error" | "success" | "warning" | "info" | "pending" | "unknown"} />
                      </div>
                      <span className="text-sm text-gray-500">{node.layer}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">依赖: </span>
                        {node.dependencies.length > 0 ? node.dependencies.join(', ') : '无'}
                      </div>
                      <div>
                        <span className="text-gray-500">被依赖: </span>
                        {node.dependents.length > 0 ? node.dependents.join(', ') : '无'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无拓扑数据"
                description="系统拓扑结构将在数据收集后显示"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Patterns Tab */}
      {activeTab === 'patterns' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                历史模式
              </CardTitle>
              <Button size="sm" onClick={() => setShowPatternModal(true)}>
                <Plus className="h-4 w-4 mr-1" />
                学习模式
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {patterns.patterns.length > 0 ? (
              <div className="space-y-4">
                {patterns.patterns.map((pattern) => (
                  <div key={pattern.pattern_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{pattern.root_cause}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">置信度: {(pattern.confidence * 100).toFixed(1)}%</span>
                        <span className="text-sm text-gray-500">频率: {pattern.frequency}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">最后发生: </span>
                        {new Date(pattern.last_occurrence).toLocaleString()}
                      </div>
                      <div>
                        <span className="text-gray-500">平均解决时间: </span>
                        {pattern.resolution_time_avg.toFixed(1)}分钟
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无历史模式"
                description="历史模式将在故障解决后自动学习"
                action={<Button onClick={() => setShowPatternModal(true)}>学习第一个模式</Button>}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Hypotheses Tab */}
      {activeTab === 'hypotheses' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              活跃假设
            </CardTitle>
          </CardHeader>
          <CardContent>
            {hypotheses.hypotheses.length > 0 ? (
              <div className="space-y-4">
                {hypotheses.hypotheses.map((hypothesis) => (
                  <div key={hypothesis.hypothesis_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{hypothesis.root_cause}</span>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={hypothesis.verification_status as "error" | "success" | "warning" | "info" | "pending" | "unknown"} />
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteHypothesis(hypothesis.hypothesis_id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">置信度: </span>
                        {(hypothesis.confidence * 100).toFixed(1)}%
                      </div>
                      <div>
                        <span className="text-gray-500">影响分数: </span>
                        {hypothesis.impact_score.toFixed(1)}
                      </div>
                    </div>
                    <div className="mt-2 text-sm">
                      <span className="text-gray-500">因果路径: </span>
                      {hypothesis.causal_path.join(' → ')}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="暂无活跃假设"
                description="根因分析将生成假设列表"
                action={<Button onClick={() => setActiveTab('analysis')}>开始分析</Button>}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Analysis Tab */}
      {activeTab === 'analysis' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                根因分析
              </CardTitle>
              <Button size="sm" onClick={() => setShowAnalysisModal(true)}>
                <Plus className="h-4 w-4 mr-1" />
                创建分析
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <EmptyState
              title="根因分析功能"
              description="基于告警和指标数据进行智能根因分析"
              action={<Button onClick={() => setShowAnalysisModal(true)}>创建第一个分析</Button>}
            />
          </CardContent>
        </Card>
      )}

      {/* Root Cause Analysis Modal */}
      <EnhancedModal
        open={showAnalysisModal}
        onOpenChange={setShowAnalysisModal}
        title="根因分析"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">告警ID</label>
            <input
              type="text"
              value={String(analysisData.alert.id || '')}
              onChange={(e) => setAnalysisData({ ...analysisData, alert: { ...analysisData.alert, id: e.target.value } })}
              placeholder="输入告警ID"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowAnalysisModal(false)}>
              取消
            </Button>
            <Button onClick={handleRootCauseAnalysis} disabled={analyzeRootCauseMutation.isPending}>
              {analyzeRootCauseMutation.isPending ? '分析中...' : '分析'}
            </Button>
          </div>
        </div>
      </EnhancedModal>

      {/* Pattern Learning Modal */}
      <EnhancedModal
        open={showPatternModal}
        onOpenChange={setShowPatternModal}
        title="学习历史模式"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">根因</label>
            <input
              type="text"
              value={patternData.root_cause}
              onChange={(e) => setPatternData({ ...patternData, root_cause: e.target.value })}
              placeholder="输入根因描述"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">解决时间（分钟）</label>
            <input
              type="number"
              value={String(patternData.resolution_time)}
              onChange={(e) => setPatternData({ ...patternData, resolution_time: Number(e.target.value) })}
              placeholder="输入解决时间"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">有效性评分</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={String(patternData.effectiveness)}
              onChange={(e) => setPatternData({ ...patternData, effectiveness: Number(e.target.value) })}
              placeholder="输入有效性评分 (0-1)"
              className="w-full px-3 py-2 border rounded-md bg-white"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowPatternModal(false)}>
              取消
            </Button>
            <Button onClick={handlePatternLearning} disabled={learnPatternMutation.isPending}>
              {learnPatternMutation.isPending ? '学习中...' : '学习'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}