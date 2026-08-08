'use client'

import { useEffect, useRef, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';
import G6, { Graph } from '@antv/g6';

interface RootCauseNode {
  id: string;
  type: 'service' | 'metric' | 'alert';
  name: string;
  status: 'normal' | 'warning' | 'critical';
  probability: number;
}

interface RootCausePath {
  nodes: string[];
  probability: number;
  impact: number;
}

interface RootCauseReport {
  id: string;
  alertId: string;
  possibleCauses: {
    service: string;
    probability: number;
    description: string;
    evidence: string[];
  }[];
  impactAnalysis: {
    affectedServices: string[];
    userImpact: string;
    businessImpact: string;
  };
  relatedMetrics: {
    name: string;
    value: number;
    trend: 'up' | 'down' | 'stable';
  }[];
}

interface Alert {
  id: string;
  title: string;
  desc?: string;
  metric?: string;
  value?: number;
  level?: string;
}

function getStatusColor(status: string) {
  switch (status) {
    case 'critical':
      return 'bg-red-100 text-red-800';
    case 'warning':
      return 'bg-yellow-100 text-yellow-800';
    case 'normal':
      return 'bg-green-100 text-green-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

function getTrendIcon(trend: string) {
  switch (trend) {
    case 'up':
      return '📈';
    case 'down':
      return '📉';
    case 'stable':
      return '➡️';
    default:
      return '➡️';
  }
}

const RootCauseGraph: React.FC<{ nodes: RootCauseNode[]; paths: RootCausePath[] }> = ({ nodes, paths }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!graphRef.current) {
      graphRef.current = new G6.Graph({
        container: containerRef.current,
        width: containerRef.current.offsetWidth,
        height: containerRef.current.offsetHeight,
        fitView: true,
        fitViewPadding: 20,
        defaultNode: {
          type: 'circle',
          size: 30,
          style: { stroke: '#fff', lineWidth: 2 },
          labelCfg: { style: { fill: '#000', fontSize: 12 } },
        },
        defaultEdge: {
          style: { stroke: '#f97316', lineWidth: 2, endArrow: true },
          labelCfg: { style: { fill: '#6b7280', fontSize: 10 } },
        },
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node'],
        },
      });
    }

    const graph = graphRef.current;
    const nodeMap = new Map<string, RootCauseNode>();
    nodes.forEach((n) => nodeMap.set(n.id, n));
    paths.forEach((p) =>
      p.nodes.forEach((name) => {
        if (!nodeMap.has(name)) {
          nodeMap.set(name, { id: name, name, type: 'service', status: 'normal', probability: 0 });
        }
      })
    );
    const allNodes = Array.from(nodeMap.values());

    const width = containerRef.current.offsetWidth || 600;
    const height = containerRef.current.offsetHeight || 320;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 40;

    const g6Nodes = allNodes.map((n, i) => {
      const angle = allNodes.length > 1 ? (2 * Math.PI * i) / allNodes.length : 0;
      const x = allNodes.length > 1 ? centerX + radius * Math.cos(angle) : centerX;
      const y = allNodes.length > 1 ? centerY + radius * Math.sin(angle) : centerY;
      const fill = n.type === 'alert' ? '#ef4444' : n.type === 'metric' ? '#22c55e' : '#3b82f6';
      return { id: n.id, label: n.name, x, y, style: { fill } };
    });

    const edgeSet = new Set<string>();
    const g6Edges: { source: string; target: string }[] = [];
    paths.forEach((p) => {
      for (let i = 1; i < p.nodes.length; i += 1) {
        const key = `${p.nodes[i - 1]}->${p.nodes[i]}`;
        if (!edgeSet.has(key)) {
          edgeSet.add(key);
          g6Edges.push({ source: p.nodes[i - 1], target: p.nodes[i] });
        }
      }
    });

    graph.changeData({ nodes: g6Nodes, edges: g6Edges });
    graph.fitView();
  }, [nodes, paths]);

  if (nodes.length === 0) {
    return (
      <div className="h-80 bg-gray-50 rounded-lg flex items-center justify-center text-gray-500">
        暂无根因数据
      </div>
    );
  }

  return <div ref={containerRef} className="h-80 bg-gray-50 rounded-lg" />;
};

export default function RootCausePage() {
  const [selectedAlert, setSelectedAlert] = useState<string>('');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [rootCauseReport, setRootCauseReport] = useState<RootCauseReport | null>(null);
  const [rootCauseNodes, setRootCauseNodes] = useState<RootCauseNode[]>([]);
  const [rootCausePaths, setRootCausePaths] = useState<RootCausePath[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  useEffect(() => {
    const loadAlerts = async () => {
      setAlertsLoading(true);
      try {
        const res = await api.get('/api/v1/alerts?limit=50');
        const list: Alert[] = res.data?.alerts || [];
        setAlerts(list);
        if (list.length > 0) {
          setSelectedAlert((prev) => (prev && list.find((a) => a.id === prev) ? prev : list[0].id));
        }
      } catch (err) {
        console.error('加载告警失败', err);
      } finally {
        setAlertsLoading(false);
      }
    };
    loadAlerts();
  }, []);

  useEffect(() => {
    const fetchHypotheses = async () => {
      try {
        const res = await api.get('/api/v1/root-cause/hypotheses');
        const hypotheses = res.data?.hypotheses || [];
        applyHypotheses(hypotheses);
      } catch {
        // api interceptor already shows toast errors
      }
    };
    fetchHypotheses();
  }, []);

  const applyHypotheses = (hypotheses: any[]) => {
    setRootCausePaths(
      hypotheses.map((h: any) => ({
        nodes: Array.isArray(h.causal_path) && h.causal_path.length > 0 ? h.causal_path : [h.root_cause],
        probability: Math.round((h.confidence || 0) * 100),
        impact: Math.round((h.impact_score || 0) * 100),
      }))
    );

    const nodeMap = new Map<string, RootCauseNode>();
    hypotheses.forEach((h: any) => {
      const confidence = Math.round((h.confidence || 0) * 100);
      const upsert = (name: string) => {
        const existing = nodeMap.get(name);
        const probability = existing ? Math.max(existing.probability, confidence) : confidence;
        const isMetric = /CPU|内存|使用率|响应时间|错误率|请求量|负载|metric/i.test(name);
        const isAlert = /告警|alert|ALT-/i.test(name);
        const type: RootCauseNode['type'] = isAlert ? 'alert' : isMetric ? 'metric' : 'service';
        const status: RootCauseNode['status'] = probability >= 80 ? 'critical' : probability >= 50 ? 'warning' : 'normal';
        nodeMap.set(name, { id: name, type, name, status, probability });
      };
      upsert(h.root_cause);
      (h.causal_path || []).forEach(upsert);
    });
    setRootCauseNodes(Array.from(nodeMap.values()));
  };

  const handleAnalyze = async () => {
    const alert = alerts.find((a) => a.id === selectedAlert);
    if (!alert) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const res = await api.post('/api/v1/root-cause/analyze', {
        alert: {
          id: alert.id,
          title: alert.title,
          service: alert.metric || 'unknown',
          value: alert.value,
          level: alert.level,
        },
        metrics_data: {},
        context: {},
      });
      const hypotheses = res.data?.hypotheses || [];
      const total = hypotheses.length;
      applyHypotheses(hypotheses);

      const affectedServices = (Array.from(
        new Set(hypotheses.flatMap((h: any) => h.causal_path || []).filter(Boolean))
      ) as string[]).filter((s) => typeof s === 'string');
      const maxConfidence = total
        ? Math.round(Math.max(...hypotheses.map((h: any) => h.confidence || 0)) * 100)
        : 0;

      const report: RootCauseReport = {
        id: `RCR-${alert.id}`,
        alertId: res.data?.alert_id || alert.id,
        possibleCauses: hypotheses.map((h: any) => ({
          service: h.root_cause,
          probability: Math.round((h.confidence || 0) * 100),
          description: `${h.root_cause}${h.causal_path?.length ? ' → ' + h.causal_path.join(' → ') : ''}`,
          evidence: Array.isArray(h.evidence) ? h.evidence : [],
        })),
        impactAnalysis: {
          affectedServices,
          userImpact: total
            ? affectedServices.length
              ? `识别出 ${affectedServices.length} 个受影响服务`
              : '未识别到受影响服务'
            : '—',
          businessImpact: total ? `最高置信度：${maxConfidence}%` : '—',
        },
        relatedMetrics: [],
      };
      setRootCauseReport(report);
    } catch (err: any) {
      setAnalyzeError(err?.response?.data?.detail || '根因分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">根因分析</h1>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">选择告警</label>
              <Select value={selectedAlert} onChange={(e) => setSelectedAlert(e.target.value)}>
                {alerts.map((alert) => (
                  <option key={alert.id} value={alert.id}>
                    {alert.title} {alert.metric ? `(${alert.metric})` : ''}
                  </option>
                ))}
              </Select>
              {alertsLoading && <p className="text-xs text-gray-500 mt-1">加载告警中…</p>}
            </div>
            <Button onClick={handleAnalyze} disabled={!selectedAlert || analyzing}>
              {analyzing ? '分析中…' : '开始分析'}
            </Button>
          </div>
          {analyzeError && <p className="text-sm text-red-600 mt-2">{analyzeError}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>根因图谱</CardTitle>
        </CardHeader>
        <CardContent>
          <RootCauseGraph nodes={rootCauseNodes} paths={rootCausePaths} />
          <div className="mt-4 flex gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full" />
              <span>告警节点</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full" />
              <span>服务节点</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-500 rounded-full" />
              <span>指标节点</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-1 bg-orange-500" />
              <span>根因路径</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>根因路径</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {rootCausePaths.map((path, index) => (
              <div key={index} className="p-4 border border-orange-200 bg-orange-50 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">路径 {index + 1}</span>
                    <Badge className="bg-orange-100 text-orange-800">
                      概率: {path.probability}%
                    </Badge>
                    <Badge className="bg-purple-100 text-purple-800">
                      影响度: {path.impact}%
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  {path.nodes.map((node, i) => (
                    <span key={i}>
                      <span className="px-2 py-1 bg-white border border-gray-300 rounded">{node}</span>
                      {i < path.nodes.length - 1 && <span className="text-gray-400 mx-1">→</span>}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            {rootCausePaths.length === 0 && (
              <p className="text-sm text-gray-500">暂无根因路径数据</p>
            )}
          </div>
        </CardContent>
      </Card>

      {rootCauseReport && (
        <Card>
          <CardHeader>
            <CardTitle>根因分析报告</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h4 className="font-medium mb-3">可能根因 (按概率排序)</h4>
                <div className="space-y-3">
                  {rootCauseReport.possibleCauses.map((cause, index) => (
                    <div key={index} className="p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{cause.service}</span>
                          <Badge className={cause.probability >= 80 ? 'bg-red-100 text-red-800' : cause.probability >= 50 ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}>
                            概率: {cause.probability}%
                          </Badge>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{cause.description}</p>
                      <div className="space-y-1">
                        <p className="text-xs text-gray-500">证据:</p>
                        {cause.evidence.map((evidence, i) => (
                          <p key={i} className="text-sm text-gray-700 ml-2">• {evidence}</p>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-3">影响范围分析</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">受影响服务</p>
                    <div className="flex flex-wrap gap-1">
                      {rootCauseReport.impactAnalysis.affectedServices.map((service) => (
                        <Badge key={service} variant="outline" className="text-xs">
                          {service}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <p className="text-sm text-gray-500 mb-1">用户影响</p>
                    <p className="text-sm">{rootCauseReport.impactAnalysis.userImpact}</p>
                  </div>
                  <div className="p-4 border border-gray-200 rounded-lg md:col-span-2">
                    <p className="text-sm text-gray-500 mb-1">业务影响</p>
                    <p className="text-sm">{rootCauseReport.impactAnalysis.businessImpact}</p>
                  </div>
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-3">相关指标趋势</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {rootCauseReport.relatedMetrics.map((metric) => (
                    <div key={metric.name} className="p-4 border border-gray-200 rounded-lg">
                      <p className="text-sm text-gray-500 mb-1">{metric.name}</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold">{metric.value}</span>
                        <span className="text-lg">{getTrendIcon(metric.trend)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <Button>导出报告</Button>
                <Button variant="outline">查看详情</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
