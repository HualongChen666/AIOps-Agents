'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { Slider } from '@/components/ui/slider';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import {
  Network,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  RefreshCw,
  Zap,
  Brain,
  GitBranch,
  Target,
  FileText,
  BarChart3,
  Settings
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
  predicted_impact: Record<string, number>;
}

interface PredictionResult {
  prediction_horizon: number;
  predicted_root_causes: Array<{
    root_cause: string;
    probability: number;
    expected_time: number;
    pattern_id: string;
  }>;
  confidence: number;
  model_used: string;
}

interface VerificationResult {
  hypothesis_id: string;
  verification_status: string;
  verification_timestamp: string;
  verification_score: number;
  checks: Array<{
    check: string;
    passed: boolean;
    details: string;
  }>;
}

interface CrossLayerPath {
  path: string[];
  path_length: number;
  alert_id: string;
}

export default function RootCauseAdvancedPage() {
  const [selectedAlert, setSelectedAlert] = useState<string>('');
  const [maxDepth, setMaxDepth] = useState<number>(5);
  const [predictionHorizon, setPredictionHorizon] = useState<number>(60);
  const [similarityThreshold, setSimilarityThreshold] = useState<number>(0.5);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isPredicting, setIsPredicting] = useState(false);
  const [selectedHypothesis, setSelectedHypothesis] = useState<RootCauseHypothesis | null>(null);
  const [crossLayerPath, setCrossLayerPath] = useState<CrossLayerPath | null>(null);
  const [predictionResult, setPredictionResult] = useState<PredictionResult | null>(null);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);

  // 🔧 从真实告警服务拉取上下文（消除写死的样例请求体）
  const loadAlertContext = async () => {
    const resp = await api.get('/api/v1/alerts/', { params: { limit: 200 } });
    const alerts: any[] = resp.data?.alerts || [];
    const alertRecord =
      alerts.find((a) => String(a.id ?? a.alert_id ?? a.alertId) === selectedAlert) || null;
    return { alerts, alertRecord };
  };

  const buildAlertPayload = (a: any) => ({
    id: String(a.id ?? a.alert_id ?? selectedAlert),
    title: a.title,
    description: a.desc ?? a.description ?? '',
    severity: a.level ?? a.severity ?? 'unknown',
    timestamp: a.timestamp ?? a.raw_time ?? new Date().toISOString(),
    service: a.service ?? a.service_name ?? 'unknown',
    source: a.source ?? 'unknown',
    host: a.host ?? a.hostname ?? '',
    affected_services: a.affected_services ?? [],
    affected_components: a.affected_components ?? [],
  });

  const buildMetricsPayload = (a: any) => {
    const value = Number(a?.value ?? 0) || 0;
    const metric = String(a?.metric ?? '').toLowerCase();
    return {
      cpu_usage: metric === 'cpu' ? value : 0,
      memory_usage: metric === 'memory' ? value : 0,
      response_time: metric === 'latency' || metric === 'response_time' ? value : 0,
    };
  };

  // 获取统计信息
  const { data: statisticsData, refetch: refetchStatistics } = useQuery({
    queryKey: ['root-cause-statistics'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/root-cause/statistics');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const handleEnhancedAnalysis = async () => {
    if (!selectedAlert) {
      return;
    }

    setIsAnalyzing(true);
    try {
      const { alertRecord } = await loadAlertContext();
      if (!alertRecord) {
        window.alert('未找到告警: ' + selectedAlert);
        setIsAnalyzing(false);
        return;
      }
      const alertData = buildAlertPayload(alertRecord);
      const metricsData = buildMetricsPayload(alertRecord);
      const context = { max_steps: 5 };

      const resp = await api.post('/api/v1/root-cause/analyze', {
        alert: alertData,
        metrics_data: metricsData,
        context: context,
      });

      if (resp.data?.hypotheses && resp.data.hypotheses.length > 0) {
        setSelectedHypothesis(resp.data.hypotheses[0]);
      }

      refetchStatistics();
    } catch (error: any) {
      console.error('Enhanced root cause analysis failed:', error);
      if (error.response?.status === 503) {
        alert('根因智能引擎不可用，请检查后端服务配置');
      } else {
        alert('增强分析失败: ' + (error.response?.data?.detail || error.message));
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleCrossLayerTracking = async () => {
    if (!selectedAlert) {
      return;
    }

    try {
      const { alertRecord } = await loadAlertContext();
      if (!alertRecord) {
        window.alert('未找到告警: ' + selectedAlert);
        return;
      }
      const alertData = buildAlertPayload(alertRecord);

      const resp = await api.post('/api/v1/root-cause/cross-layer-track', alertData, {
        params: { max_depth: maxDepth },
      });

      setCrossLayerPath(resp.data);
    } catch (error: any) {
      console.error('Cross-layer tracking failed:', error);
      alert('跨层跟踪失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handlePatternMatching = async () => {
    try {
      const { alerts: recentAlerts } = await loadAlertContext();
      const symptoms = {
        alerts: recentAlerts.slice(0, 10).map((a) => ({
          alert_type: a.metric ?? a.title ?? 'unknown',
          host: a.host ?? a.source ?? '',
        })),
        metrics: buildMetricsPayload(recentAlerts[0] ?? {}),
      };

      const resp = await api.post('/api/v1/root-cause/patterns/match', {
        symptoms: symptoms,
        similarity_threshold: similarityThreshold,
      });

      alert(`匹配到 ${resp.data.total_matches} 个历史模式`);
    } catch (error: any) {
      console.error('Pattern matching failed:', error);
      alert('模式匹配失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleRootCausePrediction = async () => {
    setIsPredicting(true);
    try {
      const { alerts: recentAlerts } = await loadAlertContext();
      const currentState = {
        ...buildMetricsPayload(recentAlerts[0] ?? {}),
        services: recentAlerts.slice(0, 10).map((a) => ({
          name: a.service ?? a.service_name ?? 'unknown',
          health: a.level ?? a.severity ?? 'unknown',
        })),
      };

      const resp = await api.post('/api/v1/root-cause/predict', {
        current_state: currentState,
        prediction_horizon: predictionHorizon,
      });

      setPredictionResult(resp.data);
    } catch (error: any) {
      console.error('Root cause prediction failed:', error);
      alert('根因预测失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsPredicting(false);
    }
  };

  const handleVerifyHypothesis = async () => {
    if (!selectedHypothesis) {
      return;
    }

    try {
      const { alertRecord } = await loadAlertContext();
      const verificationData = {
        affected_components: alertRecord?.affected_components ?? [],
        observed_symptoms: alertRecord
          ? [String(alertRecord.metric ?? alertRecord.title ?? 'alert')]
          : [],
        metrics: buildMetricsPayload(alertRecord ?? {}),
        last_state: { status: 'running' },
      };

      const resp = await api.post('/api/v1/root-cause/verify', {
        hypothesis_id: selectedHypothesis.hypothesis_id,
        verification_data: verificationData,
      });

      setVerificationResult(resp.data.verification_result);
      refetchStatistics();
    } catch (error: any) {
      console.error('Verification failed:', error);
      alert('验证失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleLearnPattern = async () => {
    try {
      const { alerts: recentAlerts } = await loadAlertContext();
      const symptoms = {
        alerts: recentAlerts.slice(0, 10).map((a) => ({
          alert_type: a.metric ?? a.title ?? 'unknown',
          host: a.host ?? a.source ?? '',
        })),
        metrics: buildMetricsPayload(recentAlerts[0] ?? {}),
      };

      const resp = await api.post('/api/v1/root-cause/patterns/learn', {
        symptoms: symptoms,
        root_cause: selectedHypothesis?.root_cause ?? recentAlerts[0]?.title ?? 'unknown',
        resolution_time: 0,
        effectiveness: 0,
      });

      alert('模式学习成功: ' + resp.data.message);
      refetchStatistics();
    } catch (error: any) {
      console.error('Pattern learning failed:', error);
      alert('模式学习失败: ' + (error.response?.data?.detail || error.message));
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
      case 'in_progress':
        return 'bg-blue-500';
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
      case 'in_progress':
        return '验证中';
      default:
        return '待验证';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">高级根因分析</h1>
          <p className="text-sm text-gray-500 mt-1">跨层跟踪、预测与自动化验证</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetchStatistics()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新统计
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
                  <p className="text-sm font-medium text-gray-600">验证准确率</p>
                  <p className="text-2xl font-bold">
                    {((statisticsData.statistics?.pattern_match_accuracy || 0) * 100).toFixed(1)}%
                  </p>
                </div>
                <Target className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="enhanced-analysis" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="enhanced-analysis">增强分析</TabsTrigger>
          <TabsTrigger value="cross-layer">跨层跟踪</TabsTrigger>
          <TabsTrigger value="prediction">根因预测</TabsTrigger>
          <TabsTrigger value="verification">自动化验证</TabsTrigger>
          <TabsTrigger value="pattern-learning">模式学习</TabsTrigger>
        </TabsList>

        {/* 增强分析标签页 */}
        <TabsContent value="enhanced-analysis" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                增强根因分析
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="输入告警ID..."
                  value={selectedAlert}
                  onChange={(e) => setSelectedAlert(e.target.value)}
                  className="flex-1"
                />
                <Button
                  onClick={handleEnhancedAnalysis}
                  disabled={!selectedAlert || isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      分析中...
                    </>
                  ) : (
                    <>
                      <Brain className="h-4 w-4 mr-2" />
                      开始分析
                    </>
                  )}
                </Button>
              </div>

              {selectedHypothesis && (
                <div className="mt-6 space-y-4">
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h3 className="font-semibold text-blue-900 mb-3">分析结果</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="font-medium">根因:</span>
                        <span className="font-semibold">{selectedHypothesis.root_cause}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-medium">置信度:</span>
                        <Badge className="bg-blue-500">
                          {(selectedHypothesis.confidence * 100).toFixed(1)}%
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-medium">影响评分:</span>
                        <Badge variant="outline">
                          {selectedHypothesis.impact_score.toFixed(2)}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-medium">推荐操作:</span>
                        <span>{selectedHypothesis.recommended_action}</span>
                        {selectedHypothesis.requires_approval && (
                          <Badge variant="destructive" className="ml-2">需要审批</Badge>
                        )}
                      </div>
                      <div>
                        <span className="font-medium">因果路径:</span>
                        <div className="mt-1 text-xs text-gray-600 bg-white p-2 rounded">
                          {selectedHypothesis.causal_path.join(' → ')}
                        </div>
                      </div>
                    </div>
                  </div>

                  {selectedHypothesis.expected_observations.length > 0 && (
                    <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                      <h4 className="font-semibold text-green-900 mb-2">预期观察</h4>
                      <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                        {selectedHypothesis.expected_observations.map((obs, idx) => (
                          <li key={idx}>{obs}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedHypothesis.missing_data.length > 0 && (
                    <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                      <h4 className="font-semibold text-yellow-900 mb-2">缺失数据</h4>
                      <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                        {selectedHypothesis.missing_data.map((data, idx) => (
                          <li key={idx}>{data}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedHypothesis.evidence.length > 0 && (
                    <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                      <h4 className="font-semibold text-purple-900 mb-2">证据链</h4>
                      <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                        {selectedHypothesis.evidence.map((evidence, idx) => (
                          <li key={idx}>{evidence}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 跨层跟踪标签页 */}
        <TabsContent value="cross-layer" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5" />
                跨层跟踪
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">告警ID</label>
                  <Input
                    placeholder="输入告警ID..."
                    value={selectedAlert}
                    onChange={(e) => setSelectedAlert(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    最大深度: {maxDepth}
                  </label>
                  <Slider
                    value={[maxDepth]}
                    onValueChange={(value) => setMaxDepth(value[0])}
                    min={1}
                    max={10}
                    step={1}
                  />
                </div>
                <Button
                  onClick={handleCrossLayerTracking}
                  disabled={!selectedAlert}
                  className="w-full"
                >
                  <GitBranch className="h-4 w-4 mr-2" />
                  执行跨层跟踪
                </Button>
              </div>

              {crossLayerPath && (
                <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h3 className="font-semibold text-blue-900 mb-3">跟踪结果</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium">告警ID:</span> {crossLayerPath.alert_id}
                    </div>
                    <div>
                      <span className="font-medium">路径长度:</span> {crossLayerPath.path_length}
                    </div>
                    <div>
                      <span className="font-medium">因果路径:</span>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {crossLayerPath.path.map((node, idx) => (
                          <div key={idx} className="flex items-center">
                            <Badge variant="outline">{node}</Badge>
                            {idx < crossLayerPath.path.length - 1 && (
                              <span className="mx-1 text-gray-400">→</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 根因预测标签页 */}
        <TabsContent value="prediction" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                根因预测
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    预测时间窗口 (分钟): {predictionHorizon}
                  </label>
                  <Slider
                    value={[predictionHorizon]}
                    onValueChange={(value) => setPredictionHorizon(value[0])}
                    min={10}
                    max={180}
                    step={10}
                  />
                </div>
                <Button
                  onClick={handleRootCausePrediction}
                  disabled={isPredicting}
                  className="w-full"
                >
                  {isPredicting ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      预测中...
                    </>
                  ) : (
                    <>
                      <TrendingUp className="h-4 w-4 mr-2" />
                      执行根因预测
                    </>
                  )}
                </Button>
              </div>

              {predictionResult && (
                <div className="mt-6 space-y-4">
                  <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                    <h3 className="font-semibold text-purple-900 mb-3">预测结果</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="font-medium">预测时间窗口:</span>
                        <span>{predictionResult.prediction_horizon} 分钟</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-medium">使用模型:</span>
                        <Badge variant="outline">{predictionResult.model_used}</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-medium">整体置信度:</span>
                        <Badge className="bg-purple-500">
                          {(predictionResult.confidence * 100).toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                  </div>

                  {predictionResult.predicted_root_causes.length > 0 && (
                    <div className="p-4 bg-gray-50 rounded-lg border">
                      <h4 className="font-semibold mb-3">预测的根因</h4>
                      <div className="space-y-2">
                        {predictionResult.predicted_root_causes.map((pred, idx) => (
                          <div key={idx} className="p-3 bg-white rounded border">
                            <div className="flex justify-between items-center mb-2">
                              <span className="font-medium">{pred.root_cause}</span>
                              <Badge>
                                {(pred.probability * 100).toFixed(1)}%
                              </Badge>
                            </div>
                            <div className="text-xs text-gray-600 space-y-1">
                              <div>预期发生时间: {pred.expected_time.toFixed(1)} 分钟</div>
                              <div>模式ID: {pred.pattern_id}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 自动化验证标签页 */}
        <TabsContent value="verification" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                自动化验证
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-gray-50 rounded-lg border">
                <h4 className="font-medium mb-2">当前选中的假设</h4>
                {selectedHypothesis ? (
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium">假设ID:</span> {selectedHypothesis.hypothesis_id}
                    </div>
                    <div>
                      <span className="font-medium">根因:</span> {selectedHypothesis.root_cause}
                    </div>
                    <div>
                      <span className="font-medium">置信度:</span>
                      <Badge>
                        {(selectedHypothesis.confidence * 100).toFixed(1)}%
                      </Badge>
                    </div>
                    <div>
                      <span className="font-medium">验证状态:</span>
                      <Badge className={getVerificationStatusColor(selectedHypothesis.verification_status)}>
                        {getVerificationStatusText(selectedHypothesis.verification_status)}
                      </Badge>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">请先执行增强分析以生成假设</p>
                )}
              </div>

              <Button
                onClick={handleVerifyHypothesis}
                disabled={!selectedHypothesis}
                className="w-full"
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                执行自动化验证
              </Button>

              {verificationResult && (
                <div className="mt-6 space-y-4">
                  <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                    <h3 className="font-semibold text-green-900 mb-3">验证结果</h3>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="font-medium">验证状态:</span>
                        <Badge className={getVerificationStatusColor(verificationResult.verification_status)}>
                          {getVerificationStatusText(verificationResult.verification_status)}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="font-medium">验证分数:</span>
                        <Badge variant="outline">
                          {(verificationResult.verification_score * 100).toFixed(1)}%
                        </Badge>
                      </div>
                      <div>
                        <span className="font-medium">验证时间:</span>
                        <span className="ml-2">
                          {new Date(verificationResult.verification_timestamp).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-gray-50 rounded-lg border">
                    <h4 className="font-semibold mb-3">验证检查项</h4>
                    <div className="space-y-2">
                      {verificationResult.checks.map((check, idx) => (
                        <div key={idx} className="flex items-start gap-2 p-2 bg-white rounded">
                          <CheckCircle className={`h-4 w-4 mt-0.5 ${check.passed ? 'text-green-500' : 'text-red-500'}`} />
                          <div className="flex-1">
                            <div className="font-medium text-sm">{check.check}</div>
                            <div className="text-xs text-gray-600">{check.details}</div>
                          </div>
                          <Badge variant={check.passed ? 'default' : 'destructive'}>
                            {check.passed ? '通过' : '失败'}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 模式学习标签页 */}
        <TabsContent value="pattern-learning" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                历史模式学习
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    相似度阈值: {similarityThreshold.toFixed(2)}
                  </label>
                  <Slider
                    value={[similarityThreshold]}
                    onValueChange={(value) => setSimilarityThreshold(value[0])}
                    min={0}
                    max={1}
                    step={0.05}
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handlePatternMatching}
                    variant="outline"
                    className="flex-1"
                  >
                    <Activity className="h-4 w-4 mr-2" />
                    匹配历史模式
                  </Button>
                  <Button
                    onClick={handleLearnPattern}
                    className="flex-1"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    学习新模式
                  </Button>
                </div>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h3 className="font-semibold text-blue-900 mb-2">模式学习说明</h3>
                <div className="text-sm text-gray-700 space-y-2">
                  <p>• <strong>匹配历史模式:</strong> 将当前症状与历史模式进行匹配，找到相似的根因</p>
                  <p>• <strong>学习新模式:</strong> 从已解决的故障中学习新的历史模式，提升未来分析准确性</p>
                  <p>• <strong>相似度阈值:</strong> 控制模式匹配的严格程度，值越高匹配越严格</p>
                  <p>• <strong>模式包含:</strong> 症状签名、根因、频率、置信度、平均解决时间、有效性评分</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
